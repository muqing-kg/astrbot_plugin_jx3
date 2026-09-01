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
    """Run one query while rotating group-owned credentials."""
    cursors.setdefault("token", 0)
    cursors.setdefault("ticket", 0)
    token_values = list(await sessions.list_active_credentials(umo, "token"))
    ticket_values = list(await sessions.list_active_credentials(umo, "ticket"))

    if token_required and not token_values:
        return token_missing
    if ticket_required and not ticket_values:
        return ticket_missing

    token_order = _rotated(token_values, cursors["token"])
    ticket_order = _rotated(ticket_values, cursors["ticket"])
    token_failures: list[str] = []
    ticket_failures: list[str] = []
    for token_index, token_value in enumerate(token_order or [""]):
        for ticket_index, ticket_value in enumerate(ticket_order or [""]):
            try:
                result = await runner(token_value, ticket_value)
                if token_values:
                    cursors["token"] = (
                        cursors["token"] + token_index + 1
                    ) % len(token_values)
                if ticket_values:
                    cursors["ticket"] = (
                        cursors["ticket"] + ticket_index + 1
                    ) % len(ticket_values)
                return result
            except CredentialRuntimeError as exc:
                kind = exc.kind
                value = token_value if kind == "token" else ticket_value
                reason = exc.reason
                if kind == "token":
                    confirmed, reason = await confirm_token_failure(jx3api, value)
                    if confirmed:
                        await sessions.remove_pool_token(umo, value, reason)
                        if notify:
                            await notify(f"已停用接口令牌 {masked_credential(value)}：{reason}")
                    else:
                        reason = f"未能确认失效：{reason}"
                    token_failures.append(f"{masked_credential(value)}：{reason}")
                    break
                if kind == "ticket":
                    confirmed, reason = await confirm_ticket_failure(jx3api, value, token_value)
                    if confirmed:
                        await sessions.delete_pool_ticket(umo, value)
                        if notify:
                            await notify(f"已移除推栏标识 {masked_credential(value)}：{reason}")
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
    """Move removed interface tokens back to the pool when quota is restored."""
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
    return restored
