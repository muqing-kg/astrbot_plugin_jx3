from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .credentials import (
    CredentialRuntimeError,
    confirm_ticket_failure,
    inspect_token_status,
    masked_credential,
)
from .plugin_log import logger


LABELS = {"token": "接口令牌", "ticket": "推栏标识"}


def _rotated(values: list[str], start: int) -> list[str]:
    if not values:
        return []
    return values[start % len(values):] + values[:start % len(values)]


async def _credential_source(
    sessions: Any,
    umo: str,
    kind: str,
) -> tuple[str, list[str], str]:
    source, values = await sessions.resolve_credential_pool(umo, kind)
    return source, list(values), f"{source}_{kind}"


async def execute_query_with_credentials(
    runner: Callable[[str, str], Awaitable[Any]],
    *,
    jx3api: Any,
    sessions: Any,
    umo: str,
    cursors: dict[str, int],
    token_required: bool,
    ticket_required: bool,
    token_missing: str,
    ticket_missing: str,
    notify: Callable[[str], Awaitable[None]] | None = None,
) -> Any:
    """Run one query while rotating group-owned or global credentials."""
    token_source, token_values, token_cursor_key = await _credential_source(
        sessions, umo, "token"
    )
    ticket_source, ticket_values, ticket_cursor_key = await _credential_source(
        sessions, umo, "ticket"
    )
    cursors.setdefault(token_cursor_key, 0)
    cursors.setdefault(ticket_cursor_key, 0)

    if token_required and not token_values:
        return token_missing
    if ticket_required and not ticket_values:
        return ticket_missing

    token_order = _rotated(token_values, cursors[token_cursor_key])
    ticket_order = _rotated(ticket_values, cursors[ticket_cursor_key])
    token_failures: list[str] = []
    ticket_failures: list[str] = []
    for token_index, token_value in enumerate(token_order or [""]):
        for ticket_index, ticket_value in enumerate(ticket_order or [""]):
            try:
                result = await runner(token_value, ticket_value)
                if token_values:
                    cursors[token_cursor_key] = (
                        cursors[token_cursor_key] + token_index + 1
                    ) % len(token_values)
                if ticket_values:
                    cursors[ticket_cursor_key] = (
                        cursors[ticket_cursor_key] + ticket_index + 1
                    ) % len(ticket_values)
                return result
            except CredentialRuntimeError as exc:
                kind = exc.kind
                value = token_value if kind == "token" else ticket_value
                reason = exc.reason
                if kind == "token":
                    if token_source == "group":
                        await sessions.remove_pool_credential(umo, "token", value, reason)
                        action = "已停用群属接口令牌"
                    elif token_source == "global":
                        await sessions.remove_global_credential("token", value, reason)
                        action = "已停用全局接口令牌"
                    else:
                        action = "接口令牌不可用"
                    if notify:
                        await notify(f"{action} {masked_credential(value)}：{reason}")
                    logger.warning(
                        f"{action}，原因：{reason}",
                        extra={"log_source": "query", "log_umo": umo, "log_action": "credential_rotation"},
                    )
                    token_failures.append(f"{masked_credential(value)}：{reason}")
                    break
                if kind == "ticket":
                    confirmed, reason = await confirm_ticket_failure(jx3api, value, token_value)
                    if confirmed:
                        if ticket_source == "group":
                            await sessions.delete_pool_credential(umo, "ticket", value)
                            action = "已移除群属推栏标识"
                        elif ticket_source == "global":
                            await sessions.delete_global_credential_by_value("ticket", value)
                            action = "已移除全局推栏标识"
                        else:
                            action = "推栏标识不可用"
                        if notify:
                            await notify(f"{action} {masked_credential(value)}：{reason}")
                        logger.warning(
                            f"{action}，原因：{reason}",
                            extra={"log_source": "query", "log_umo": umo, "log_action": "credential_rotation"},
                        )
                    else:
                        reason = f"未能确认失效：{reason}"
                    ticket_failures.append(f"{masked_credential(value)}：{reason}")
                    continue
                raise

    failures = token_failures + ticket_failures
    detail = "；".join(failures)
    if token_failures:
        return f"接口令牌 {detail}"
    return f"推栏标识 {detail}"


async def restore_recoverable_tokens(jx3api: Any, sessions: Any) -> list[str]:
    """Move recovered tokens from failure pools back to active pools."""
    await sessions.purge_expired_removed_credentials(30)
    restored: list[str] = []
    for kind in ("token", "push_token"):
        for row in await sessions.list_removed_credentials(kind):
            umo = str(row.get("umo") or "")
            value = str(row.get("value") or "").strip()
            if not umo or not value:
                continue
            state, _reason, _remaining = await inspect_token_status(jx3api, value)
            if state == "ok" and await sessions.add_active_credential(umo, kind, value):
                restored.append(value)
        for row in await sessions.list_removed_global_credentials(kind):
            value = str(row.get("value") or "").strip()
            if not value:
                continue
            state, _reason, _remaining = await inspect_token_status(jx3api, value)
            if state == "ok" and await sessions.restore_global_credential(kind, value):
                restored.append(value)
    return restored
