from __future__ import annotations

from typing import Any

from .session_policy import (
    is_group_umo,
    is_placeholder_display_name,
    parse_umo,
)


def _group_info_payload(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {}
    data = response.get("data")
    return data if isinstance(data, dict) else response


async def fetch_group_display_name(context: Any, umo: str) -> str:
    """Fetch a OneBot group name for a persisted group UMO."""
    if not is_group_umo(umo):
        return ""
    platform_id, _, group_id = parse_umo(umo)
    if not platform_id or not group_id:
        return ""
    try:
        platform = context.get_platform_inst(platform_id)
        bot = getattr(platform, "bot", None)
        call_action = getattr(bot, "call_action", None)
        if not callable(call_action):
            return ""
        response = await call_action("get_group_info", group_id=group_id)
        info = _group_info_payload(response)
        name = str(info.get("group_name") or info.get("name") or "").strip()
    except Exception:
        return ""
    return "" if is_placeholder_display_name(name, group_id) else name


async def ensure_group_display_name(
    context: Any,
    sessions: Any,
    umo: str,
    row: dict[str, Any] | None,
) -> dict[str, Any]:
    """Reuse a real event name, and replace legacy ID placeholders."""
    _, _, group_id = parse_umo(umo)
    if not is_placeholder_display_name((row or {}).get("display_name"), group_id):
        return row or {}
    name = await fetch_group_display_name(context, umo)
    if not name:
        return row or {}
    return await sessions.ensure(umo, name, is_private=False)


async def refresh_missing_group_display_names(
    context: Any,
    sessions: Any,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Backfill missing display names while listing persisted sessions."""
    for index, row in enumerate(rows):
        umo = str(row.get("umo") or "")
        _, _, group_id = parse_umo(umo)
        if not is_placeholder_display_name(row.get("display_name"), group_id):
            continue
        name = await fetch_group_display_name(context, umo)
        if not name:
            continue
        updated = await sessions.ensure(umo, name, is_private=False)
        if updated:
            rows[index] = updated
    return rows
