from __future__ import annotations

from typing import Any

from astrbot.api import logger

from .session_policy import is_group_umo, parse_umo


async def leave_group(context: Any, umo: str) -> tuple[bool, str]:
    """Best-effort leave. Platform adapters define whether this is possible."""
    if not is_group_umo(umo):
        return False, "只能退群聊会话"

    platform_id, _, group_id = parse_umo(umo)
    platform = context.get_platform_inst(platform_id)
    if not platform:
        return False, "未找到消息平台"

    platform_name = str(platform.meta().name or "").lower()
    if platform_name != "aiocqhttp":
        return False, "当前平台不支持自动退群"

    bot = getattr(platform, "bot", None)
    if not bot:
        return False, "平台客户端不可用"
    try:
        await bot.call_action("set_group_leave", group_id=group_id)
        return True, ""
    except Exception as exc:
        logger.warning(f"自动退群失败: {umo}, error={exc}")
        return False, str(exc).strip() or "平台接口调用失败"
