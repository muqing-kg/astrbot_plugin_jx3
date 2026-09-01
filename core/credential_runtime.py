from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .credentials import (
    CredentialRuntimeError,
    confirm_token_failure,
    confirm_ticket_failure,
    masked_credential,
    validate_pool_token,
)


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
    group_values = list(await sessions.list_active_credentials(umo, kind))
    if group_values:
        return "group", group_values, f"group_{kind}"
    global_values = list(await sessions.list_active_global_credentials(kind))
    if global_values:
        return "global", global_values, f"global_{kind}"
    return "none", [], f"none_{kind}"


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
                    confirmed, reason = await confirm_token_failure(jx3api, value)
                    if confirmed:
                        if token_source == "group":
                            await sessions.remove_pool_token(umo, value, reason)
                            action = "已停用接口令牌"
                        elif token_source == "global":
                            await sessions.skip_global_token(value, reason)
                            action = "已跳过全局接口令牌"
                        else:
                            action = "接口令牌不可用"
                        if notify:
                            await notify(f"{action} {masked_credential(value)}：{reason}")
                    else:
                        reason = f"未能确认失效：{reason}"
                    token_failures.append(f"{masked_credential(value)}：{reason}")
                    break
                if kind == "ticket":
                    confirmed, reason = await confirm_ticket_failure(jx3api, value, token_value)
                    if confirmed:
                        if ticket_source == "group":
                            await sessions.delete_pool_ticket(umo, value)
                            action = "已移除推栏标识"
                        elif ticket_source == "global":
                            await sessions.delete_global_ticket(value)
                            action = "已移除全局推栏标识"
                        else:
                            action = "推栏标识不可用"
                        if notify:
                            await notify(f"{action} {masked_credential(value)}：{reason}")
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
    """Move removed group tokens and skipped global tokens back when restored."""
    if hasattr(sessions, "list_removed_credentials"):
        rows = await sessions.list_removed_credentials("token")
    else:
        rows = await sessions.list_credentials("", "token", "removed")
    restored: list[str] = []
    for row in rows:
        umo = str(row.get("umo") or "")
        value = str(row.get("value") or "").strip()
        if not umo or not value:
            continue
        ok, _message, _remaining = await validate_pool_token(jx3api, value)
        if ok and await sessions.add_active_credential(umo, "token", value):
            restored.append(value)
    for row in await sessions.list_skipped_global_credentials():
        value = str(row.get("value") or "").strip()
        if not value:
            continue
        ok, _message, _remaining = await validate_pool_token(jx3api, value)
        if ok and await sessions.restore_global_token(value):
            restored.append(value)
    return restored
