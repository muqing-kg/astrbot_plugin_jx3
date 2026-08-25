from __future__ import annotations

from copy import deepcopy

OFFICIAL_SERVERS = [
    "飞龙在天",
    "天鹅坪",
    "破阵子",
    "眉间雪",
    "山海相逢",
    "蝶恋花",
    "剑胆琴心",
    "斗转星移",
    "乾坤一掷",
    "长安城",
    "龙争虎斗",
    "唯我独尊",
    "梦江南",
    "绝代天骄",
    "幽月轮",
]

# Sourced from jx3-help/external/jx3instructions/src/tools/dicts.ts
# Adjacent short names after an official name are aliases. Do not invent extras.
PRESET_ALIASES: dict[str, list[str]] = {
    "飞龙在天": [],
    "天鹅坪": [],
    "破阵子": ["念破"],
    "眉间雪": [],
    "山海相逢": [],
    "蝶恋花": ["蝶服"],
    "剑胆琴心": [],
    "斗转星移": ["姨妈"],
    "乾坤一掷": ["华乾"],
    "长安城": [],
    "龙争虎斗": ["龙虎"],
    "唯我独尊": ["唯满侠"],
    "梦江南": ["双梦"],
    "绝代天骄": [],
    "幽月轮": [],
}

BLOCKED_SERVERS = {"共結來緣", "共结来缘"}


def parse_aliases(raw: str | list[str] | None) -> list[str]:
    if isinstance(raw, list):
        parts = [str(item) for item in raw]
    else:
        text = str(raw or "")
        parts = re_split(text)
    seen: set[str] = set()
    aliases: list[str] = []
    for part in parts:
        name = part.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        aliases.append(name)
    return aliases


def re_split(text: str) -> list[str]:
    buf = []
    current = []
    for ch in text:
        if ch in {",", "，", ";", "；", "|", "/", "、", " "}:
            if current:
                buf.append("".join(current))
                current = []
            continue
        current.append(ch)
    if current:
        buf.append("".join(current))
    return buf


def default_alias_map() -> dict[str, list[str]]:
    return {server: list(PRESET_ALIASES.get(server, [])) for server in OFFICIAL_SERVERS}


def apply_alias_overrides(overrides: dict[str, str | list[str]] | None) -> dict[str, list[str]]:
    catalog = default_alias_map()
    for server, raw in (overrides or {}).items():
        catalog, error = set_server_aliases(catalog, server, raw)
        if error:
            continue
    return catalog


def _used_names(catalog: dict[str, list[str]], skip_server: str = "") -> dict[str, str]:
    used: dict[str, str] = {}
    for server in OFFICIAL_SERVERS:
        used[server] = server
        if server == skip_server:
            continue
        for alias in catalog.get(server, []):
            used[alias] = server
    return used


def set_server_aliases(
    catalog: dict[str, list[str]],
    server: str,
    raw: str | list[str] | None,
) -> tuple[dict[str, list[str]], str]:
    catalog = deepcopy(catalog)
    if server not in OFFICIAL_SERVERS:
        return catalog, "未知区服"
    aliases = parse_aliases(raw)
    used = _used_names(catalog, skip_server=server)
    for alias in aliases:
        if alias in BLOCKED_SERVERS:
            return catalog, "该名称不可用"
        owner = used.get(alias)
        if owner and owner != server:
            return catalog, f"别名已被「{owner}」占用"
        if alias in OFFICIAL_SERVERS and alias != server:
            return catalog, "不能使用其他正式区服名做别名"
    catalog[server] = aliases
    return catalog, ""


def canonical_server(catalog: dict[str, list[str]] | None, name: str) -> str:
    text = (name or "").strip()
    if not text or text in BLOCKED_SERVERS:
        return ""
    catalog = catalog or default_alias_map()
    if text in OFFICIAL_SERVERS:
        return text
    for server, aliases in catalog.items():
        if text in aliases:
            return server
    return ""


def public_server_rows(catalog: dict[str, list[str]] | None = None) -> list[dict]:
    catalog = catalog or default_alias_map()
    rows = []
    for server in OFFICIAL_SERVERS:
        aliases = catalog.get(server, [])
        rows.append({
            "server": server,
            "aliases": aliases,
            "aliases_text": "，".join(aliases),
        })
    return rows

