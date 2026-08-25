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
    "关隘": "push_guanai",
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

# 全服事件不按绑定区服过滤。
GLOBAL_KINDS = frozenset({"新闻", "更新", "八卦", "云从", "微博"})

# 官方 action -> 开关名。
ACTION_KIND = {
    2001: "开服",
    2002: "新闻",
    2003: "更新",
    2004: "八卦",
    2005: "关隘",
    2006: "云从",
    1001: "奇遇",
    1002: "刷马",
    1003: "刷马",
    1005: "扶摇",
    1006: "扶摇",
    1008: "的卢",
    1009: "的卢",
    1010: "的卢",
    1011: "的卢",
    1012: "掉落",
    1013: "拍卖",
    1014: "诛恶",
    1015: "追魂",
    1017: "祭祀",
    1018: "关隘",
    1101: "宣战",
    1102: "宣战",
    1103: "宣战",
    1104: "宣战",
    1105: "宣战",
    1111: "据点",
    1112: "据点",
    1113: "据点",
    1114: "据点",
    1115: "据点",
    1116: "据点",
    1117: "据点",
    1118: "据点",
    1119: "据点",
    1120: "据点",
    1121: "据点",
    1122: "据点",
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
            {"action": 2005, "name": "关隘首领", "kind": "关隘"},
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
            {"action": 1008, "name": "的卢每日", "kind": "的卢"},
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
            {"action": 1018, "name": "关隘首领", "kind": "关隘"},
            {"action": 1101, "name": "领地宣战开始", "kind": "宣战"},
            {"action": 1102, "name": "领地宣战结束", "kind": "宣战"},
            {"action": 1103, "name": "帮会宣战开始", "kind": "宣战"},
            {"action": 1104, "name": "帮会宣战结束", "kind": "宣战"},
            {"action": 1105, "name": "帮会约战完胜", "kind": "宣战"},
            {"action": 1111, "name": "抢占粮仓", "kind": "据点"},
            {"action": 1112, "name": "大旗重置", "kind": "据点"},
            {"action": 1113, "name": "大旗被夺", "kind": "据点"},
            {"action": 1114, "name": "据点占领", "kind": "据点"},
            {"action": 1115, "name": "据点占领(无帮会)", "kind": "据点"},
            {"action": 1116, "name": "小攻防贡献(非开战)", "kind": "据点"},
            {"action": 1117, "name": "小攻防贡献", "kind": "据点"},
            {"action": 1118, "name": "大攻防贡献", "kind": "据点"},
            {"action": 1119, "name": "战利品竞拍", "kind": "据点"},
            {"action": 1120, "name": "小攻防分红", "kind": "据点"},
            {"action": 1121, "name": "大攻防分红", "kind": "据点"},
            {"action": 1122, "name": "大攻防分红(含指挥)", "kind": "据点"},
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
    server = data.get("server") or ""
    zone = data.get("zone") or data.get("zoneName") or ""
    where = " · ".join(part for part in (zone, server) if part)

    if action == 2001:
        status = data.get("status")
        state = "开服" if str(status) in {"1", "True", "true"} or status == 1 else "维护"
        return f"【{server or '未知区服'}】{state}了！"
    if action == 2002:
        return "\n".join(
            part for part in (
                str(data.get("type") or "官方新闻"),
                str(data.get("title") or ""),
                str(data.get("url") or ""),
                str(data.get("date") or ""),
            ) if part
        )
    if action == 2003:
        return (
            "游戏客户端检查到新版本\n"
            f"当前版本：{data.get('now_version') or '未知'}\n"
            f"新版本：{data.get('new_version') or '未知'}\n"
            f"更新包数：{data.get('package_num') or 0}\n"
            f"更新包大小：{data.get('package_size') or '未知'}"
        )
    if action == 2004:
        return "\n".join(
            part for part in (
                str(data.get("title") or "八卦速报"),
                str(data.get("url") or ""),
                str(data.get("date") or ""),
                f"来自{data.get('tieba') or data.get('name') or '未知'}吧" if (data.get("tieba") or data.get("name")) else "",
            ) if part
        )
    if action == 2005:
        return f"【{data.get('server') or '未知区服'}】关隘首领进入{data.get('stage') or '未知'}阶段"
    if action == 2006:
        title = data.get("name") or "云从预告"
        site = data.get("site") or ""
        desc = data.get("desc") or ""
        when = _fmt_time(data.get("time"))
        lines = [str(title)]
        if site:
            lines.append(f"地点：{site}")
        if desc:
            lines.append(str(desc))
        if when:
            lines.append(f"时间：{when}")
        return "\n".join(lines)
    if action == 1001:
        return f"{where}的【{data.get('name') or '未知'}】触发了 {data.get('event') or '奇遇'}"
    if action == 1002:
        return f"{where} 马驹刷新：{data.get('map_name') or '未知地图'}"
    if action == 1003:
        return f"{where} 【{data.get('name') or '未知'}】捕获了{data.get('horse') or '马驹'}（{data.get('map_name') or '未知地图'}）"
    if action == 1005:
        return f"{where} 扶摇已开启"
    if action == 1006:
        names = data.get("name") or "未知"
        if isinstance(names, list):
            names = "、".join(str(item) for item in names if str(item).strip()) or "未知"
        return f"{where} 扶摇点名：{names}"
    if action == 1008:
        return f"{where} 的卢每日：{data.get('map_name') or ''} {data.get('name') or ''}".strip()
    if action == 1009:
        return f"{where} 的卢刷新：{data.get('map_name') or '未知地图'}"
    if action == 1010:
        return f"{where} {data.get('capture_camp_name') or ''} {data.get('capture_role_name') or ''} 捕获的卢（{data.get('map_name') or ''}）".strip()
    if action == 1011:
        return f"{where} {data.get('auction_role_name') or ''} 拍得的卢 {data.get('auction_amount') or ''}".strip()
    if action == 1012:
        return f"{where} {data.get('role_name') or ''} 在{data.get('map_name') or ''} 获得 {data.get('item_name') or ''} x{data.get('item_amount') or ''}".strip()
    if action == 1013:
        return f"{where} {data.get('role_name') or ''} 拍得 {data.get('item_name') or ''} x{data.get('item_amount') or ''}".strip()
    if action == 1014:
        return f"{where} 诛恶刷新：{data.get('map_name') or '未知地图'}"
    if action == 1015:
        return f"{where} 追魂点名：{data.get('role_name') or '未知'}（{data.get('role_server') or ''}）"
    if action == 1017:
        return f"{where} {data.get('tong_name') or ''} 祭祀 {data.get('castle_name') or ''}".strip()
    if action == 1018:
        return f"{where} 关隘首领 {data.get('leader_name') or ''} 进入{data.get('stage_name') or '未知'}阶段"
    if action in {1101, 1103}:
        return f"{where} {data.get('declaring_tong_name') or ''} 向 {data.get('accepting_tong_name') or ''} 宣战"
    if action in {1102, 1104}:
        return f"{where} 宣战结束：{data.get('victory_tong_name') or data.get('declaring_tong_name') or ''}"
    if action == 1105:
        return f"{where} 约战结束，胜方：{data.get('victory_tong_name') or '未知'}"
    if action == 1111:
        return f"{where} 抢占粮仓：{data.get('castle_name') or ''}（{data.get('camp_name') or ''}）"
    if action == 1112:
        return f"{where} 大旗重置：{data.get('castle_name') or ''}"
    if action == 1113:
        return f"{where} 大旗被夺：{data.get('castle_name') or ''}（{data.get('camp_name') or ''}）"
    if action in {1114, 1115}:
        owner = data.get("tong_name") or data.get("camp_name") or ""
        return f"{where} 据点占领：{data.get('castle_name') or ''} {owner}".strip()
    if action in {1116, 1117, 1118}:
        return f"{where} {data.get('tong_name') or ''} 贡献排行更新"
    if action == 1119:
        return f"{where} {data.get('role_name') or ''} 拍得 {data.get('item_name') or ''} x{data.get('item_amount') or ''}".strip()
    if action in {1120, 1121, 1122}:
        return f"{where} {data.get('tong_name') or data.get('chief_tong_name') or ''} 分红 {data.get('split_amount') or ''}".strip()
    if action == 1201:
        return "\n".join(
            part for part in (
                str(data.get("user_name") or "微博更新"),
                str(data.get("article_text") or ""),
                str(data.get("url") or ""),
            ) if part
        )
    kind = resolve_push_kind(action) or "事件"
    return f"{kind}推送\n{where}".strip()


def build_notice_view(display_name: str, server: str, enabled: set[str] | list[str] | None = None) -> dict[str, Any]:
    enabled_set = {str(item) for item in (enabled or [])}
    groups = []
    for group in EVENT_GROUPS:
        items = []
        enabled_count = 0
        for item in group["items"]:
            on = item["kind"] in enabled_set
            if on:
                enabled_count += 1
            items.append({
                "action": item["action"],
                "name": item["name"],
                "kind": item["kind"],
                "enabled": on,
            })
        groups.append({
            "name": group["name"],
            "enabled_count": enabled_count,
            "total": len(items),
            "items": items,
        })
    return {
        "title": "通知管理",
        "display_name": display_name or "当前会话",
        "server": server or "未绑定",
        "groups": groups,
    }
