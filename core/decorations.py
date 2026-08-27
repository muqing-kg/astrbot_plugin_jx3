import random
import html

import aiohttp
from jinja2 import Environment


_JINJA = Environment(autoescape=False)

_DECOR_COLORS = ("#f3b6c4", "#efb3c3", "#f5cdd7", "#f9dbe3")
_DECOR_KINDS = ("heart", "star", "sparkle", "diamond", "paw", "flower", "moon", "cloud")
_DECOR_SVG = {
    "heart": '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor"><path d="M12 21C12 21 3.5 15.7 2 10.6 0.9 6.9 3.4 3.5 7 3.5c2.2 0 3.9 1.3 5 3.1 1.1-1.8 2.8-3.1 5-3.1 3.6 0 6.1 3.4 5 7.1C20.5 15.7 12 21 12 21z"/></svg>',
    "star": '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor"><path d="M12 2.4l2.8 6 6.6.7-5 4.4 1.4 6.5L12 16.8 6.2 20l1.4-6.5-5-4.4 6.6-.7z"/></svg>',
    "sparkle": '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor"><path d="M12 2l2.1 7.9L22 12l-7.9 2.1L12 22l-2.1-7.9L2 12l7.9-2.1z"/></svg>',
    "diamond": '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor"><path d="M12 2.5 19.5 9 12 21.5 4.5 9z"/></svg>',
    "paw": '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor"><path d="M6.3 8.1c1 0 1.9-.9 1.9-2.1S7.4 4 6.4 4 4.5 4.8 4.5 6s.8 2.1 1.8 2.1zm5.7.2c1.2 0 2.2-1 2.2-2.4S13.2 3.6 12 3.6 9.8 4.7 9.8 6s1 2.3 2.2 2.3zm5.6-.2c1.1 0 2-.9 2-2.1s-.8-2-1.9-2-2 .9-2 2.1.8 2 1.9 2zM3.6 12.5c1.3 0 2.4-1.2 2.4-2.7S4.9 7.2 3.6 7.2 1.3 8.4 1.3 9.8s1.1 2.7 2.3 2.7zm8.4 0c1.5 0 2.7-1.4 2.7-3.2 0-1.8-1.2-3.2-2.7-3.2S9.3 7.5 9.3 9.3c0 1.8 1.2 3.2 2.7 3.2zm7.4-.5c1.3 0 2.4-1.2 2.4-2.7s-1.1-2.9-2.4-2.9-2.3 1.2-2.3 2.7 1 2.9 2.3 2.9zM18 14.9c-2.4-.3-3.6.4-4.9 1.1-1 .6-2 1.1-3.4 1.1-1.6 0-2.7-.8-4.2-1.2-1.1-.3-2.5-.4-4.1.6v2.1c2-1.3 3.2-1 4.3-.7 1.4.4 2.5 1.1 4.3 1.1 1.4 0 2.6-.5 3.8-1.2 1.2-.7 2.4-1.5 4.8-1.1z"/></svg>',
    "flower": '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor"><path d="M12 9.2A3.5 3.5 0 0 1 9 3.8a3.3 3.3 0 0 1 6 0A3.5 3.5 0 0 1 12 9.2zm0 0a3.5 3.5 0 0 0 6.8-1 3.3 3.3 0 0 0-6.8 1zm0 0a3.5 3.5 0 0 1-6.8 1 3.3 3.3 0 0 1 6.8-1zm.5 5.4c1.9.2 3.8-.5 4.3-2.7-2-1-4.2-.4-4.3 2.7zm-1 0c-1.9.2-3.8-.5-4.3-2.7 2-1 4.2-.4 4.3 2.7zm2.8 4.2c-.2 1.9-2.3 3-4.2 2.2-.8-.3-1.4-.9-1.7-1.7h5.9z"/></svg>',
    "moon": '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor"><path d="M20.8 15.1A9 9 0 0 1 8.9 3.2a9 9 0 1 0 11.9 12.6z"/></svg>',
    "cloud": '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor"><path d="M6.8 19h10.4a4.4 4.4 0 0 0 .8-8.7A6.2 6.2 0 0 0 6 7.7a5 5 0 0 0 .8 10.3z"/></svg>',
  }
_DECOR_SPOTS = {
    "header": [
        "left: 7%; top: 10px;",
        "left: 46%; bottom: 10px;",
        "right: 212px; top: 14px;",
        "left: 13%; bottom: 12px;",
        "left: 58%; top: 12px;",
        "right: 224px; bottom: 12px;",
        "left: 90px; top: 58%;",
        "left: 38%; top: 54%;",
        "right: 118px; top: 56%;",
        "right: 40px; bottom: 10px;",
        "left: 47%; top: 24px;",
        "right: 176px; top: 38px;",
        "left: 30%; top: 16px;",
        "left: 24%; bottom: 10px;",
    ],
    "body": [
        "left: 3%; top: 3%;",
        "right: 3%; top: 3%;",
        "left: 10px; top: 12%;",
        "right: 10px; top: 14%;",
        "left: 5%; top: 30%;",
        "right: 5%; top: 32%;",
        "left: 13%; top: 48%; transform: translateY(-50%);",
        "right: 13%; top: 50%; transform: translateY(-50%);",
        "left: 4%; top: 70%;",
        "right: 4%; top: 72%;",
        "left: 6%; bottom: 8%;",
        "right: 6%; bottom: 8%;",
        "left: 40%; top: 6%;",
        "right: 40%; top: 10%;",
        "left: 42%; top: 46%; transform: translateY(-50%);",
        "right: 42%; bottom: 20%;",
    ],
    "foot": [
        "left: 5%; top: 50%; transform: translateY(-50%);",
        "right: 5%; top: 50%; transform: translateY(-50%);",
        "left: 12%; top: 22%;",
        "right: 12%; top: 20%;",
        "left: 24%; top: 50%; transform: translateY(-50%);",
        "right: 24%; top: 50%; transform: translateY(-50%);",
        "left: 40%; top: 14%;",
        "right: 42%; top: 12%;",
        "left: 48%; bottom: 8px;",
        "right: 46%; bottom: 10px;",
        "left: 70%; top: 20%;",
        "right: 68%; top: 24%;",
    ],
}

_POEM_SOURCES = (
    ("https://v1.jinrishici.com/all.json", ("content",)),
    ("https://v1.hitokoto.cn/?c=i&encode=json&charset=utf-8", ("hitokoto",)),
)
_ACTION_SPOTS = (
    ("left: -24px; top: 6px;", 16),
    ("right: -20px; top: -8px;", 12),
    ("left: 6px; bottom: -18px;", 14),
    ("right: 12px; bottom: -20px;", 10),
    ("left: -14px; bottom: 10px;", 9),
)
def _deco_svg(kind: str) -> str:
    return _DECOR_SVG.get(kind, _DECOR_SVG["heart"])


def _build_decor_markup(zone: str, max_count: int, min_count: int = 1) -> str:
    spots = _DECOR_SPOTS.get(zone) or []
    if not spots:
        return ""
    count = random.randint(min_count, max_count)
    picked = random.sample(range(len(spots)), min(count, len(spots)))
    parts = []
    opacity_floor, opacity_ceil = (0.2, 0.36) if zone == "body" else (0.26, 0.48)
    for index in picked:
        kind = random.choice(_DECOR_KINDS)
        size = random.randint(14, 26)
        color = random.choice(_DECOR_COLORS)
        opacity = round(random.uniform(opacity_floor, opacity_ceil), 2)
        parts.append(
            f'<span class="jx3-deco" style="{spots[index]} width: {size}px; height: {size}px; '
            f'color: {color}; opacity: {opacity};">{_deco_svg(kind)}</span>'
        )
    return "".join(parts)


def _build_action_markup() -> str:
    picked = random.sample(range(len(_ACTION_SPOTS)), random.randint(3, 5))
    parts = []
    for index in picked:
        style, size = _ACTION_SPOTS[index]
        kind = random.choice(_DECOR_KINDS)
        color = random.choice(_DECOR_COLORS)
        opacity = round(random.uniform(0.4, 0.65), 2)
        parts.append(
            f'<span class="jx3-action-deco" style="{style} width: {size}px; height: {size}px; '
            f'color: {color}; opacity: {opacity};">{_deco_svg(kind)}</span>'
        )
    return "".join(parts)


async def fetch_poem_line() -> str:
    """拉取一句随机诗词，本地无网络时返回空串。"""
    for url, keys in _POEM_SOURCES:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status != 200:
                        continue
                    payload = await resp.json(content_type=None)
            for key in keys:
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        except Exception:
            continue
    return ""


_BODY_DECOR_RANGES = (
    (35000, (12, 16)),
    (12000, (8, 12)),
    (3000, (6, 10)),
    (0, (4, 6)),
)


def _estimate_payload_weight(payload: dict) -> int:
    """模板无法本地渲染时按数据体量估算。"""
    if not isinstance(payload, dict):
        return 0
    total = 0
    stack = list(payload.values())
    while stack:
        value = stack.pop()
        if isinstance(value, str):
            total += len(value)
        elif isinstance(value, (list, tuple)):
            total += len(value) * 24
            stack.extend(value)
        elif isinstance(value, dict):
            stack.extend(value.values())
    return total


def estimate_body_length(template: str, payload: dict, icons: dict | None = None) -> int:
    """本地渲染一次并用 main 卡片长度估算正文图片长度，失败回退数据权重。"""
    render_payload = dict(payload)
    render_payload.setdefault("icons", icons or {})
    try:
        html = _JINJA.from_string(template or "").render(**render_payload)
    except Exception:
        return _estimate_payload_weight(payload)
    start_tag = '<main class="jx3-card jx3-card--body">'
    start = html.find(start_tag)
    if start < 0:
        return _estimate_payload_weight(payload)
    end = html.find("</main>", start)
    if end < 0:
        return len(html)
    return end - start - len(start_tag)


def _body_decor_range(body_length: int) -> tuple[int, int]:
    for threshold, count_range in _BODY_DECOR_RANGES:
        if body_length >= threshold:
            return count_range
    return (1, 1)


def build_decorated_payload(icons: dict, body_length: int = 0, poem_line: str = "") -> dict:
    """为模板补充随机顶卡动作图和卡片淡色矢量装饰。"""
    actions = [name for name in (icons.get("img") or {}) if name.startswith("动作")]
    brand = '<span class="jx3-bot-name">唐小珂 · 江湖小助手</span>'
    if poem_line.strip():
        deco_caption = brand + f'<span class="jx3-bot-poem">{html.escape(poem_line.strip())}</span>'
    else:
        deco_caption = brand
    return {
        "icons": icons,
        "action_icon": random.choice(actions) if actions else "",
        "deco_caption": deco_caption,
        "deco_action": _build_action_markup() if actions else "",
        "deco_header": _build_decor_markup("header", 8, 3),
        "deco_body": _build_decor_markup(
            "body",
            _body_decor_range(body_length)[1],
            _body_decor_range(body_length)[0],
        ),
        "deco_foot": _build_decor_markup("foot", 8, 3),
    }
