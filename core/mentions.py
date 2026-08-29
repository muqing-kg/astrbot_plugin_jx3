from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any


_ID_KEYS = (
    "qq", "uid", "user_id", "target_id", "id", "wxid", "to_wxid",
    "v3_username", "username", "to_username", "user", "to_user",
    "qid", "tiny_id",
)
_NAME_KEYS = ("qq_nickname", "nickname", "name", "alias", "display_name", "card", "gcard")


def component_type(item: Any) -> str:
    raw_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
    if not raw_type:
        raw_type = type(item).__name__
    return str(getattr(raw_type, "value", raw_type)).lower()


def _sources(item: Any) -> Iterable[Any]:
    yield item
    data = item.get("data") if isinstance(item, dict) else getattr(item, "data", None)
    if isinstance(data, dict):
        yield data


def _read_value(item: Any, keys: tuple[str, ...]) -> str:
    for source in _sources(item):
        for key in keys:
            if isinstance(source, dict):
                value = source.get(key)
            else:
                if not hasattr(source, key):
                    continue
                value = getattr(source, key, None)
            if value not in (None, ""):
                return str(value).strip()
    return ""


def _chains(event: Any) -> list[list[Any]]:
    chains: list[list[Any]] = []
    for source in (getattr(event, "get_messages", None), getattr(event, "get_message", None)):
        try:
            value = source() if callable(source) else None
        except Exception:
            value = None
        if value is None:
            continue
        for nested in (value, getattr(value, "chain", None), getattr(value, "components", None)):
            if isinstance(nested, (list, tuple)):
                chains.append(list(nested))

    message_obj = getattr(event, "message_obj", None)
    components = getattr(message_obj, "message", None)
    if isinstance(components, (list, tuple)):
        chains.append(list(components))
    return chains


def _self_id(event: Any) -> str:
    try:
        return str(event.get_self_id() or "").strip()
    except Exception:
        return ""


def mentioned_target(event: Any) -> tuple[str, str]:
    self_id = _self_id(event)
    for items in _chains(event):
        for item in items:
            if component_type(item) not in {"at", "mention"}:
                continue
            user_id = _read_value(item, _ID_KEYS)
            if user_id in {"all", self_id}:
                continue
            name = _read_value(item, _NAME_KEYS).lstrip("@").strip()
            if user_id:
                return user_id, name
            if name:
                return "", name

    raw_text = str(getattr(event, "message_str", "") or "")
    pattern = r"\[CQ:at[^\]]*?(?:qq|wxid|uid|user_id|v3_username)=([^,\]\s]+)"
    for match in re.finditer(pattern, raw_text, re.IGNORECASE):
        candidate = match.group(1)
        if candidate not in {"all", self_id}:
            return candidate, ""

    for candidate in _at_list_from_raw(event):
        if candidate not in {"all", self_id}:
            return candidate, ""
    return "", ""


def _append_at_text(value: str, candidates: list[str]) -> None:
    text = str(value or "").strip()
    if not text:
        return
    matches = re.findall(
        r"<atuserlist>\s*(?:<!\[CDATA\[)?([^><\]]+?)(?:\]\]>)?\s*</atuserlist>",
        text,
        re.IGNORECASE,
    )
    if not matches:
        matches = re.findall(r"\b(?:atUserList|atuserlist)\b\s*[:=]\s*([^\n\r,]+)", text, re.IGNORECASE)
    for item in matches:
        for target in re.split(r"[,，;；\s]+", item):
            target = target.strip().strip("'\"")
            if target:
                candidates.append(target)


def _collect_raw(value: Any, candidates: list[str]) -> None:
    if isinstance(value, str):
        _append_at_text(value, candidates)
        return
    if not isinstance(value, (list, tuple, dict)):
        return

    records: list[Any] = []
    if isinstance(value, dict):
        records.append(value)
    else:
        records.extend(value)

    def flatten(items: Any):
        if isinstance(items, dict):
            yield items
        elif isinstance(items, (list, tuple)):
            for nested in items:
                yield from flatten(nested)

    for leaf in flatten(records):
        if isinstance(leaf, str):
            _append_at_text(leaf, candidates)
        elif isinstance(leaf, dict):
            for key in _ID_KEYS:
                inner = str(leaf.get(key) or "").strip()
                if inner:
                    candidates.append(inner)
                    break


def _at_list_from_raw(event: Any) -> list[str]:
    raw = getattr(getattr(event, "message_obj", None), "raw_message", None)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = [raw]

    candidates: list[str] = []
    _collect_raw(raw, candidates)
    result: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in result:
            result.append(candidate)
    return result


def message_text_without_bot_mentions(event: Any) -> str:
    self_id = _self_id(event)
    text = str(getattr(event, "message_str", "") or "").strip()
    if not self_id or not text:
        return text
    for block in re.findall(r"\[CQ:at[^\]]*\]", text, flags=re.IGNORECASE):
        pattern = rf"(?:qq|wxid|uid|user_id|v3_username)={re.escape(self_id)}(?:[^0-9A-Za-z_-]|$)"
        if re.search(pattern, block, flags=re.IGNORECASE):
            text = text.replace(block, "")
    return re.sub(rf"@{re.escape(self_id)}\s*", "", text).strip()


def mentioned_bot(event: Any) -> bool:
    """判断本条消息是否 @ 了机器人自身。"""
    self_id = _self_id(event)
    if not self_id:
        return False
    for items in _chains(event):
        for item in items:
            if component_type(item) in {"at", "mention"} and _read_value(item, _ID_KEYS) == self_id:
                return True
    raw_text = str(getattr(event, "message_str", "") or "")
    pattern = (
        rf"\[CQ:at[^\]]*?(?:qq|wxid|uid|user_id|v3_username)="
        rf"{re.escape(self_id)}(?:[^0-9A-Za-z_-]|$)"
    )
    if re.search(pattern, raw_text, re.IGNORECASE):
        return True
    return self_id in _at_list_from_raw(event)
