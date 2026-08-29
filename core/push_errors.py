from __future__ import annotations

from collections.abc import Iterator
from typing import Any


_PERMANENT_TEXTS = (
    "group not found",
    "group_id not found",
    "群不存在",
    "找不到群",
    "群聊不存在",
    "群聊未找到",
    "not in group",
    "bot not in group",
    "robot not in group",
    "机器人不在群",
    "不在群中",
    "不在群聊",
    "kicked from group",
    "removed from group",
    "已退出群",
    "被踢出群",
    "移出群聊",
    "已被移出",
)
_EXCEPTION_FIELDS = (
    "message",
    "msg",
    "wording",
    "reason",
    "description",
    "status",
    "status_message",
    "sub_code",
)


def _texts(value: Any, depth: int = 0) -> Iterator[str]:
    if value is None or depth > 6:
        return
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, (list, tuple, set, dict)):
        items = value.values() if isinstance(value, dict) else value
        for item in items:
            yield from _texts(item, depth + 1)
        return

    yield str(value)
    retcode = getattr(value, "retcode", None)
    if str(retcode).strip() == "1204":
        yield "group not found"
    for field in _EXCEPTION_FIELDS:
        yield from _texts(getattr(value, field, None), depth + 1)
    cause = getattr(value, "__cause__", None) or getattr(value, "__context__", None)
    yield from _texts(cause, depth + 1)


def is_permanent_group_failure(error: BaseException | None) -> bool:
    text = " ".join(str(item or "") for item in _texts(error)).lower()
    return any(item in text for item in _PERMANENT_TEXTS)
