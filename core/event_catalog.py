from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

# 开关名 -> 会话表字段。相近事件共用一个开关。
PUSH_FIELD = {
    "开服": "push_kaifu",
    "新闻": "push_xinwen",
    "更新": "push_gengxin",
    "八卦": "push_bagua",
    "云从": "push_yuncong",
    "奇遇": "push_qiyu",
    "刷马": "push_shuma",
    "扶摇": "push_fuyao",
    "的卢": "push_dilu",
    "掉落": "push_diaoluo",
    "拍卖": "push_paimai",
    "诛恶": "push_zhue",
    "追魂": "push_zhuihun",
    "祭祀": "push_jisi",
    "宣战": "push_xuanzhan",
    "据点": "push_judian",
    "微博": "push_weibo",
    "赤兔": "push_chitu",
}

PUSH_TYPES = tuple(PUSH_FIELD.keys())

# 官方事件版 OpenAPI 的接口说明。
EVENT_DESCRIPTIONS = {
    0: "赤兔到达与分享消息通知",
    1001: "奇遇触发通知",
    1002: "马驹刷新通知",
    1003: "马驹捕获通知",
    1005: "扶摇开启通知",
    1006: "扶摇点名通知",
    1009: "的卢刷新通知",
    1010: "的卢捕获通知",
    1011: "的卢拍卖通知",
    1012: "副本掉落与交易行私货通知",
    1013: "阵营拍卖通知",
    1014: "诛恶事件通知",
    1015: "追魂点名通知",
    1017: "阵营祭祀通知",
    1101: "领地宣战开始通知",
    1102: "领地宣战结束通知",
    1103: "帮会宣战开始通知",
    1104: "帮会宣战结束通知",
    1105: "帮会约战完胜通知",
    1111: "抢占粮仓通知",
    1112: "大旗重置通知",
    1113: "大旗被夺通知",
    1118: "大攻防贡献排行通知",
    1119: "大小攻防战利品竞拍通知",
    1120: "小攻防分红通知",
    1201: "微博更新通知",
    2001: "服务器开服状态变化通知",
    2002: "官方新闻更新通知",
    2003: "游戏版本更新通知",
    2004: "八卦主题更新通知",
    2006: "地图事件触发通知",
}

# 全服事件不按绑定区服过滤。
GLOBAL_KINDS = frozenset({"新闻", "更新", "八卦", "云从", "微博"})

# 官方 action -> 开关名。
ACTION_KIND = {
    2001: "开服",
    2002: "新闻",
    2003: "更新",
    2004: "八卦",
    2006: "云从",
    1001: "奇遇",
    1002: "刷马",
    1003: "刷马",
    1005: "扶摇",
    1006: "扶摇",
    1009: "的卢",
    1010: "的卢",
    1011: "的卢",
    1012: "掉落",
    1013: "拍卖",
    1014: "诛恶",
    1015: "追魂",
    1017: "祭祀",
    1101: "宣战",
    1102: "宣战",
    1103: "宣战",
    1104: "宣战",
    1105: "宣战",
    1111: "据点",
    1112: "据点",
    1113: "据点",
    1118: "据点",
    1119: "据点",
    1120: "据点",
    1201: "微博",
}

EVENT_GROUPS = [
    {
        "name": "系统通知",
        "items": [
            {"action": 2001, "name": "开服状态", "kind": "开服"},
            {"action": 2002, "name": "官方新闻", "kind": "新闻"},
            {"action": 2003, "name": "版本更新", "kind": "更新"},
            {"action": 2004, "name": "八卦速报", "kind": "八卦"},
            {"action": 2006, "name": "云从预告", "kind": "云从"},
            {"action": 0, "name": "赤兔消息", "kind": "赤兔"},
        ],
    },
    {
        "name": "世界事件",
        "items": [
            {"action": 1001, "name": "奇遇触发", "kind": "奇遇"},
            {"action": 1002, "name": "马驹刷新", "kind": "刷马"},
            {"action": 1003, "name": "马驹捕获", "kind": "刷马"},
            {"action": 1005, "name": "扶摇开启", "kind": "扶摇"},
            {"action": 1006, "name": "扶摇点名", "kind": "扶摇"},
            {"action": 1009, "name": "的卢刷新", "kind": "的卢"},
            {"action": 1010, "name": "的卢捕获", "kind": "的卢"},
            {"action": 1011, "name": "的卢拍卖", "kind": "的卢"},
            {"action": 1012, "name": "副本掉落", "kind": "掉落"},
            {"action": 1014, "name": "诛恶事件", "kind": "诛恶"},
            {"action": 1015, "name": "追魂点名", "kind": "追魂"},
        ],
    },
    {
        "name": "阵营攻防",
        "items": [
            {"action": 1013, "name": "阵营拍卖", "kind": "拍卖"},
            {"action": 1017, "name": "阵营祭祀", "kind": "祭祀"},
            {"action": 1101, "name": "领地宣战开始", "kind": "宣战"},
            {"action": 1102, "name": "领地宣战结束", "kind": "宣战"},
            {"action": 1103, "name": "帮会宣战开始", "kind": "宣战"},
            {"action": 1104, "name": "帮会宣战结束", "kind": "宣战"},
            {"action": 1105, "name": "帮会约战完胜", "kind": "宣战"},
            {"action": 1111, "name": "抢占粮仓", "kind": "据点"},
            {"action": 1112, "name": "大旗重置", "kind": "据点"},
            {"action": 1113, "name": "大旗被夺", "kind": "据点"},
            {"action": 1118, "name": "大攻防贡献", "kind": "据点"},
            {"action": 1119, "name": "战利品竞拍", "kind": "据点"},
            {"action": 1120, "name": "小攻防分红", "kind": "据点"},
        ],
    },
    {
        "name": "社交动态",
        "items": [
            {"action": 1201, "name": "微博更新", "kind": "微博"},
        ],
    },
]


def event_dedupe_key(action: int | str | None, payload: dict[str, Any] | None = None) -> str:
    data = payload or {}
    try:
        code = int(action)
    except (TypeError, ValueError):
        code = 0
    server = str(data.get("server") or "").strip()
    names = data.get("name")
    if isinstance(names, list):
        names = "、".join(str(item) for item in names if str(item).strip())
    parts = [
        str(code),
        server,
        str(data.get("status") if data.get("status") is not None else ""),
        str(data.get("time") or data.get("date") or data.get("url") or data.get("title") or ""),
        str(data.get("map_name") or data.get("event") or data.get("horse") or data.get("item_name") or ""),
        str(names or data.get("role_name") or data.get("capture_role_name") or data.get("auction_role_name") or ""),
    ]
    return ":".join(parts)


def resolve_push_kind(action: int | str | None) -> str:
    try:
        code = int(action)
    except (TypeError, ValueError):
        return ""
    return ACTION_KIND.get(code, "")


def parse_ws_message(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"action": 0, "payload": {}}
    action = raw.get("action")
    try:
        action = int(action)
    except (TypeError, ValueError):
        action = 0
    payload = raw.get("data")
    if not isinstance(payload, dict):
        payload = raw.get("detail")
    if not isinstance(payload, dict):
        payload = {}
    return {"action": action, "payload": payload, "raw": raw}


def _fmt_time(value: Any) -> str:
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return str(value or "")
    if ts > 10_000_000_000:
        ts //= 1000
    try:
        dt = datetime.fromtimestamp(ts, tz=ZoneInfo("Asia/Shanghai"))
        return dt.strftime("%m/%d %H:%M")
    except (OSError, OverflowError, ValueError):
        return str(value)


def format_event_text(action: int, payload: dict[str, Any]) -> str:
    data = payload or {}
    server = str(data.get("server") or "").strip()
    zone = str(data.get("zone") or data.get("zoneName") or "").strip()
    where = " · ".join(part for part in (zone, server) if part)

    def value(*keys):
        for key in keys:
            item = data.get(key)
            if item not in (None, ""):
                return item
        return ""

    if action == 2001:
        status = data.get("status")
        state = ""
        if status not in (None, ""):
            state = "开服" if str(status) in {"1", "True", "true"} or status == 1 else "维护"
        place = f"【{server}】" if server else ""
        if state:
            return f"{place}{state}了！"
        return f"{place}服务器状态更新"
    if action == 2002:
        return "\n".join(
            part for part in (
                str(value("type")),
                str(value("title")),
                str(value("url")),
                str(value("date")),
            ) if part
        )
    if action == 2003:
        lines = ["游戏客户端检查到新版本"]
        if value("now_version") not in (None, ""):
            lines.append(f"当前版本：{value('now_version')}")
        if value("new_version") not in (None, ""):
            lines.append(f"新版本：{value('new_version')}")
        if value("package_num") not in (None, ""):
            lines.append(f"更新包数：{value('package_num')}")
        if value("package_size") not in (None, ""):
            lines.append(f"更新包大小：{value('package_size')}")
        return "\n".join(lines)
    if action == 2004:
        source = f"来自{value('tieba', 'name')}吧" if value("tieba", "name") else ""
        return "\n".join(
            part for part in (
                str(value("title")),
                str(value("url")),
                str(value("date")),
                source,
            ) if part
        )
    if action == 2006:
        lines = []
        if value("name") not in (None, ""):
            lines.append(str(value("name")))
        if value("site") not in (None, ""):
            lines.append(f"地点：{value('site')}")
        if value("desc") not in (None, ""):
            lines.append(str(value("desc")))
        when = _fmt_time(data.get("time"))
        if when:
            lines.append(f"时间：{when}")
        return "\n".join(lines)
    if action == 1001:
        name = value("name")
        event = value("event")
        if name and event:
            core = f"【{name}】触发了 {event}"
        elif name:
            core = f"【{name}】触发奇遇"
        elif event:
            core = f"触发了 {event}"
        else:
            core = "奇遇触发"
        return "\n".join(part for part in (where, core) if part)
    if action == 1002:
        map_name = value("map_name")
        core = f"马驹刷新：{map_name}" if map_name else "马驹刷新"
        return "\n".join(part for part in (where, core) if part)
    if action == 1003:
        name = value("name")
        horse = value("horse")
        if name:
            core = f"{name} 捕获了{horse}" if horse else f"{name} 捕获马驹"
        elif horse:
            core = f"捕获了{horse}"
        else:
            core = "马驹捕获"
        map_name = value("map_name")
        if map_name:
            core = f"{core}（{map_name}）"
        return "\n".join(part for part in (where, core) if part)
    if action == 1005:
        return "\n".join(part for part in (where, "扶摇已开启") if part)
    if action == 1006:
        names = value("name")
        if isinstance(names, list):
            names = "、".join(str(item) for item in names if str(item).strip())
        core = f"扶摇点名：{names}" if names else "扶摇点名"
        return "\n".join(part for part in (where, core) if part)
    if action == 1009:
        map_name = value("map_name")
        core = f"的卢刷新：{map_name}" if map_name else "的卢刷新"
        return "\n".join(part for part in (where, core) if part)
    if action == 1010:
        core = " ".join(
            part for part in (
                str(value("capture_camp_name")),
                str(value("capture_role_name")),
                "捕获的卢",
            ) if part
        )
        map_name = value("map_name")
        if map_name:
            core = f"{core}（{map_name}）"
        return "\n".join(part for part in (where, core) if part)
    if action == 1011:
        core = " ".join(
            part for part in (
                str(value("auction_role_name")),
                "拍得的卢",
                str(value("auction_amount")),
            ) if part
        )
        return "\n".join(part for part in (where, core) if part)
    if action == 1012:
        core = " ".join(
            part for part in (
                str(value("role_name")),
                f"在{value('map_name')}" if value("map_name") else "",
                "获得",
                str(value("item_name")),
                f"x{value('item_amount')}" if value("item_amount") not in (None, "") else "",
            ) if part
        )
        return "\n".join(part for part in (where, core) if part)
    if action == 1013:
        core = " ".join(
            part for part in (
                str(value("role_name")),
                "拍得",
                str(value("item_name")),
                f"x{value('item_amount')}" if value("item_amount") not in (None, "") else "",
            ) if part
        )
        return "\n".join(part for part in (where, core) if part)
    if action == 1014:
        map_name = value("map_name")
        core = f"诛恶刷新：{map_name}" if map_name else "诛恶刷新"
        return "\n".join(part for part in (where, core) if part)
    if action == 1015:
        role = value("role_name")
        role_server = value("role_server")
        core = "追魂点名"
        if role:
            core += f"：{role}"
        if role_server:
            core += f"（{role_server}）"
        return "\n".join(part for part in (where, core) if part)
    if action == 1017:
        core = " ".join(
            part for part in (
                str(value("tong_name")),
                "祭祀",
                str(value("castle_name")),
            ) if part
        )
        return "\n".join(part for part in (where, core) if part)
    if action in {1101, 1103}:
        declaring = value("declaring_tong_name")
        accepting = value("accepting_tong_name")
        if declaring and accepting:
            core = f"{declaring} 向 {accepting} 宣战"
        elif declaring:
            core = f"{declaring} 宣战"
        elif accepting:
            core = f"向 {accepting} 宣战"
        else:
            core = "宣战"
        return "\n".join(part for part in (where, core) if part)
    if action in {1102, 1104}:
        winner = value("victory_tong_name") or value("declaring_tong_name")
        core = f"宣战结束：{winner}" if winner else "宣战结束"
        return "\n".join(part for part in (where, core) if part)
    if action == 1105:
        winner = value("victory_tong_name")
        core = f"约战结束，胜方：{winner}" if winner else "约战结束"
        return "\n".join(part for part in (where, core) if part)
    if action == 1111:
        castle, camp = value("castle_name"), value("camp_name")
        core = "抢占粮仓"
        if castle:
            core += f"：{castle}"
        if camp:
            core += f"（{camp}）"
        return "\n".join(part for part in (where, core) if part)
    if action == 1112:
        castle = value("castle_name")
        core = f"大旗重置：{castle}" if castle else "大旗重置"
        return "\n".join(part for part in (where, core) if part)
    if action == 1113:
        castle, camp = value("castle_name"), value("camp_name")
        core = "大旗被夺"
        if castle:
            core += f"：{castle}"
        if camp:
            core += f"（{camp}）"
        return "\n".join(part for part in (where, core) if part)
    if action == 1118:
        tong = value("tong_name")
        core = f"{tong} 贡献排行更新" if tong else "贡献排行更新"
        return "\n".join(part for part in (where, core) if part)
    if action == 1119:
        role = value("role_name")
        item = value("item_name")
        amount = value("item_amount")
        pieces = [str(role), "拍得", str(item)]
        if amount not in (None, ""):
            pieces.append(f"x{amount}")
        core = " ".join(piece for piece in pieces if piece)
        if core == "拍得":
            core = "战利品竞拍"
        return "\n".join(part for part in (where, core) if part)
    if action == 1120:
        tong = value("tong_name") or value("chief_tong_name")
        amount = value("split_amount")
        core = "攻防分红"
        if tong:
            core = f"{tong} 分红"
        if amount not in (None, ""):
            core += f"：{amount}"
        return "\n".join(part for part in (where, core) if part)
    if action == 1201:
        return "\n".join(
            part for part in (
                str(value("user_name")),
                str(value("article_text")),
                str(value("url")),
            ) if part
        )
    kind = resolve_push_kind(action) or ""
    return "\n".join(part for part in (kind, where) if part)


def normalize_push_overrides(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in raw.items():
        action = str(key).strip()
        name = str(value or "").strip()
        if action and name and not any(char.isspace() for char in name):
            out[action] = name
    return out


def effective_push_items(overrides: dict[str, str] | None = None) -> list[dict[str, Any]]:
    normalized = normalize_push_overrides(overrides)
    items = []
    for group in EVENT_GROUPS:
        for item in group["items"]:
            name = normalized.get(str(item["action"]), item["name"])
            items.append({**item, "name": name})
    return items


def push_arg_map(overrides: dict[str, str] | None = None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in effective_push_items(overrides):
        name = str(item["name"]).strip()
        if name:
            mapping.setdefault(name, str(item["kind"]))
    return mapping


def has_duplicate_push_names(overrides: dict[str, str] | None = None) -> bool:
    normalized = normalize_push_overrides(overrides)
    names = [str(item["name"]).strip() for item in effective_push_items(normalized)]
    return len(names) != len(set(names))


def build_notice_view(
    display_name: str,
    server: str,
    enabled: set[str] | list[str] | None = None,
    overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    enabled_set = {str(item) for item in (enabled or [])}
    normalized = normalize_push_overrides(overrides)
    groups = []
    for group in EVENT_GROUPS:
        items = []
        enabled_count = 0
        for item in group["items"]:
            on = item["kind"] in enabled_set
            if on:
                enabled_count += 1
            name = normalized.get(str(item["action"]), item["name"])
            items.append({
                "action": item["action"],
                "name": name,
                "kind": item["kind"],
                "enabled": on,
            })
        groups.append({
            "name": group["name"],
            "enabled_count": enabled_count,
            "total": len(items),
            "events": items,
        })
    return {
        "title": "通知管理",
        "display_name": display_name or "当前会话",
        "server": server or "未绑定",
        "groups": groups,
    }
