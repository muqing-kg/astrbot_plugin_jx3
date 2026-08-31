from __future__ import annotations

from dataclasses import dataclass
import re

from .event_catalog import push_arg_map

UNBOUND_SERVER = "UNBOUND_SERVER"
CREDENTIAL_MISSING = "CREDENTIAL_MISSING"
GROUP_SECRET_FORBIDDEN = "group_secret_forbidden"
CLAIM_PHRASE = "剑网3机器人"

NEED_TICKET = frozenset({
    "战绩",
    "名剑排行",
    "名剑统计",
    "阵眼",
    "资历排行",
    "技能",
    "奇穴",
    "资历分布",
})

NEED_TOKEN = frozenset({
    "赤兔", "本周赤兔", "烟花", "刷马", "马场", "沙盘",
    "战绩", "名剑排行", "名剑统计",
    "名士排行", "江湖排行", "兵甲排行", "名师排行",
    "阵营排行", "薪火排行", "家园排行",
    "浩气神兵排行", "恶人神兵排行",
    "浩气爱心排行", "恶人爱心排行",
    "赛季恶人战功榜", "赛季浩气战功榜",
    "上周恶人战功榜", "上周浩气战功榜",
    "本周恶人战功榜", "本周浩气战功榜",
    "试炼之地排行", "阵营拍卖", "的卢拍卖", "金价", "物价", "配方", "万宝楼", "诛恶",
    "名片", "全部名片", "随机名片", "查询", "未出", "汇总", "近期", "统计",
    "精耐", "百战", "成就", "角色", "阵眼", "资历排行", "技能", "奇穴", "资历",
    "掉落",
    "跨服名剑榜", "武林争霸赛", "捕快荣誉榜", "江湖浪客榜", "决斗挑战榜",
    "资历分布", "外观搜索",
    "聊天", "拜师", "收徒", "招募", "团长", "团牌",
})

# 命令最少需要的非服务器参数个数。少填了就把绑定服插到最前。
SERVER_ARITY = {
    "烟花": 1, "刷马": 0, "马场": 0, "战绩": 1,
    "名士排行": 0, "江湖排行": 0, "兵甲排行": 0, "名师排行": 0,
    "阵营排行": 0, "薪火排行": 0, "家园排行": 0,
    "浩气神兵排行": 0, "恶人神兵排行": 0,
    "浩气爱心排行": 0, "恶人爱心排行": 0,
    "赛季恶人战功榜": 0, "赛季浩气战功榜": 0,
    "上周恶人战功榜": 0, "上周浩气战功榜": 0,
    "本周恶人战功榜": 0, "本周浩气战功榜": 0,
    "试炼之地排行": 1, "阵营拍卖": 0, "的卢拍卖": 0, "金价": 0, "配方": 1,
    "帮战": 0, "沙盘": 0, "诛恶": 0, "名片": 1, "全部名片": 1, "随机名片": 0,
    "查询": 1, "未出": 1, "汇总": 0, "近期": 0,
    "精耐": 1, "成就": 2, "角色": 1, "在线": 1, "资历排行": 0, "聊天": 1, "统战": 0,
    "花价": 0, "拜师": 0, "收徒": 0, "招募": 0, "团长": 0, "团牌": 0,
    "开服": 0, "资历": 1, "交易行": 1,
    "跨服名剑榜": 0, "武林争霸赛": 0, "捕快荣誉榜": 0, "江湖浪客榜": 0, "决斗挑战榜": 0,
    "资历分布": 1,
}

# 跨服/全服榜单：不强制注入绑定区服，缺省查询返回各自真实区服。
CROSS_SERVER_COMMANDS = frozenset({
    "跨服名剑榜", "武林争霸赛", "捕快荣誉榜", "江湖浪客榜", "决斗挑战榜",
})

SERVER_SECOND_COMMANDS = frozenset({
    "物价", "统计", "掉落",
})


def mask_secret(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "未配置"
    if len(text) <= 4:
        return "已配置"
    return "****" + text[-4:]


def valid_display_name(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text and text.upper() not in {"N/A", "NULL", "NONE"})


def is_placeholder_display_name(value: object, group_id: object = "") -> bool:
    text = str(value or "").strip()
    if not valid_display_name(text):
        return True
    normalized = re.sub(r"[\s:：]+", "", text).lower()
    target = re.sub(r"[\s:：]+", "", str(group_id or "")).lower()
    if target and normalized == target:
        return True
    return bool(re.fullmatch(r"群(?:组)?[:：\s]*\d+", text, re.IGNORECASE))


def resolve_display_name(
    event_name: object,
    fallback: object = "",
    group_id: object = "",
) -> str:
    event = str(event_name or "").strip()
    if not is_placeholder_display_name(event, group_id):
        return event
    stored = str(fallback or "").strip()
    return "" if is_placeholder_display_name(stored, group_id) else stored


def resolve_query_server(explicit: str, bound: str) -> str:
    server = (explicit or "").strip()
    if server:
        return server
    bound = (bound or "").strip()
    if bound:
        return bound
    return UNBOUND_SERVER


def can_bind_session(is_admin: bool, claim_identity: str, sender_id: str) -> bool:
    if is_admin:
        return True
    claim_identity = str(claim_identity or "").strip()
    sender_id = str(sender_id or "").strip()
    return not claim_identity or claim_identity == sender_id


def is_astrbot_admin(event_is_admin: bool, sender_id: str, admin_ids: list[str] | tuple[str, ...]) -> bool:
    if event_is_admin:
        return True
    return str(sender_id or "").strip() in {str(item or "").strip() for item in admin_ids or []}


MODE_TOKENS = {"22", "33", "55", "2v2", "3v3", "5v5"}


def camp_code(camp: str) -> int:
    text = str(camp or "").strip()
    if not text or text in {"2", "恶人", "恶人谷"}:
        return 2
    if text in {"1", "浩气", "浩气盟"}:
        return 1
    raise ValueError("阵营仅支持 恶人/恶人谷、浩气/浩气盟")


SCHOOL_TAILS = {
    "万花", "纯阳", "七秀", "少林", "天策", "藏剑", "五毒", "唐门", "明教",
    "丐帮", "苍云", "长歌", "霸刀", "蓬莱", "凌雪", "衍天", "药宗", "刀宗",
    "无方", "灵素", "段氏",
}

def _is_optional_tail(cmd: str, value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    if cmd in {"战绩", "跨服名剑榜"} and text.lower() in MODE_TOKENS:
        return True
    if cmd == "武林争霸赛" and text in {"浩气", "恶人", "浩气盟", "恶人谷", "1", "2"}:
        return True
    if cmd == "决斗挑战榜" and text in {"公开", "私密", "1", "2"}:
        return True
    if cmd in {"金价", "近期", "汇总", "聊天", "资历分布", "统计", "掉落"} and text.isdigit():
        return True
    if cmd in {"随机名片", "资历排行"} and text in SCHOOL_TAILS:
        return True
    return False

UNKNOWN_SERVER = "UNKNOWN_SERVER"


def canonicalize_server_token(value: str, resolver=None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if not callable(resolver):
        return text
    official = resolver(text)
    return official or ""


def inject_server_args(cmd: str, args: list[str], bound: str, resolver=None) -> list[str] | str:
    bound = (bound or "").strip()
    if callable(resolver):
        official_bound = resolver(bound)
        if official_bound:
            bound = official_bound
    args = list(args)

    if cmd in CROSS_SERVER_COMMANDS:
        core = list(args)
        tail = []
        while core and _is_optional_tail(cmd, core[-1]):
            tail.insert(0, core.pop())
        if not core:
            return ["", tail[0]] if tail else []
        official = canonicalize_server_token(core[0], resolver)
        if official:
            return [official] + core[1:] + tail
        return core + tail

    if cmd in SERVER_ARITY:
        core = list(args)
        tail = []
        while core and _is_optional_tail(cmd, core[-1]):
            tail.insert(0, core.pop())

        official = canonicalize_server_token(core[0], resolver) if core else ""
        if official:
            return [official] + core[1:] + tail

        if not bound:
            return UNBOUND_SERVER
        return [bound] + core + tail

    if cmd in SERVER_SECOND_COMMANDS:
        if not args:
            return args
        core = list(args)
        tail = []
        while core and _is_optional_tail(cmd, core[-1]):
            tail.insert(0, core.pop())
        if len(core) >= 2:
            official = canonicalize_server_token(core[1], resolver)
            if official:
                return [core[0], official] + core[2:] + tail
            return UNKNOWN_SERVER
        if not bound:
            return UNBOUND_SERVER
        return [core[0], bound] + tail

    return args


@dataclass
class AdminCommand:
    action: str = ""
    target: str = ""
    value: str = ""
    label: str = ""
    error: str = ""


ADMIN_COMMAND_IDS = (
    "Token",
    "推送令牌",
    "推栏",
    "认领",
    "查询令牌",
    "查询推送令牌",
    "绑定",
    "打开",
    "关闭",
    "授权管理",
    "查看管理",
    "删除管理",
    "张嘴",
    "闭嘴",
)

PRIVATE_ONLY_COMMAND_IDS = {"认领", "Token", "推送令牌", "推栏"}


def remap_admin_parts(parts: list[str], catalog: dict | None) -> list[str]:
    if not parts:
        return parts
    trigger = parts[0]
    if not catalog:
        return parts
    current_names = {}
    for command_id in ADMIN_COMMAND_IDS:
        current_names[command_id] = str((catalog.get(command_id) or {}).get("command") or command_id)
    for command_id, current in current_names.items():
        if trigger == current:
            return [command_id, *parts[1:]]
        if command_id == "Token" and current == "Token" and trigger.lower() == "token":
            return ["Token", *parts[1:]]
    for command_id, current in current_names.items():
        old_names = {command_id}
        if command_id == "Token":
            old_names.add("token")
        if trigger in old_names and current not in old_names:
            return ["__renamed__", *parts[1:]]
    return parts


def parse_admin_command(
    parts: list[str],
    is_private: bool,
    push_args: dict[str, str] | None = None,
) -> AdminCommand:
    if not parts:
        return AdminCommand(error="empty")
    cmd = parts[0]
    if cmd in {"Token", "token", "接口令牌", "推栏"}:
        if not is_private:
            return AdminCommand(error=GROUP_SECRET_FORBIDDEN)
        if len(parts) < 3:
            return AdminCommand(error="missing_secret_args")
        action = "set_ticket" if cmd == "推栏" else "set_token"
        return AdminCommand(action=action, target=parts[1], value=" ".join(parts[2:]).strip())
    if cmd == "推送令牌":
        if not is_private:
            return AdminCommand(error=GROUP_SECRET_FORBIDDEN)
        if len(parts) < 3:
            return AdminCommand(error="missing_secret_args")
        return AdminCommand(action="set_push_token", target=parts[1], value=" ".join(parts[2:]).strip())
    if cmd == "认领":
        if not is_private:
            return AdminCommand(error="claim_private_only")
        return AdminCommand(action="claim", value=" ".join(parts[1:]).strip())
    if cmd == "查询令牌":
        return AdminCommand(action="token_stats")
    if cmd == "查询推送令牌":
        return AdminCommand(action="push_token_stats")
    if cmd in {"张嘴", "闭嘴"}:
        return AdminCommand(action="llm_enabled", value="1" if cmd == "张嘴" else "0")
    if cmd in {"授权管理", "查看管理", "删除管理"}:
        if is_private:
            return AdminCommand(error="group_manage_only")
        if cmd == "授权管理":
            if len(parts) < 2:
                return AdminCommand(error="missing_authorize_target")
            return AdminCommand(action="authorize", target=" ".join(parts[1:]).strip())
        if cmd == "查看管理":
            return AdminCommand(action="list_admins")
        if len(parts) < 2:
            return AdminCommand(error="missing_manager_index")
        return AdminCommand(action="deauthorize", value=parts[1].strip())
    if cmd == "绑定":
        if len(parts) < 2:
            return AdminCommand(error="missing_server")
        return AdminCommand(action="bind", value=" ".join(parts[1:]).strip())
    if cmd in {"打开", "关闭"}:
        arg = str(parts[1]).strip() if len(parts) > 1 else ""
        action = (push_args if push_args is not None else push_arg_map({})).get(arg, "")
        if not action:
            return AdminCommand(error="missing_push_type")
        return AdminCommand(
            action="open_push" if cmd == "打开" else "close_push",
            value=action,
            label=arg,
        )
    return AdminCommand(error="unknown")


def current_command_name(catalog: dict | None, command_id: str) -> str:
    if not catalog:
        return command_id
    return str((catalog.get(command_id) or {}).get("command") or command_id)


def parse_umo(umo: str) -> tuple[str, str, str]:
    parts = str(umo or "").split(":", 2)
    if len(parts) != 3:
        return "", "", ""
    platform_id, message_type, session_id = parts
    return platform_id.strip(), message_type.strip(), session_id.strip()


def is_group_umo(umo: str) -> bool:
    return parse_umo(umo)[1] == "GroupMessage"


def hint_unbound(catalog: dict | None = None) -> str:
    bind = current_command_name(catalog, "绑定")
    return (
        "当前会话未绑定区服。\n"
        f"请先由插件管理员发送：{bind} 区服名\n"
        f"例如：{bind} 梦江南"
    )


def hint_bind_ok(server: str) -> str:
    return (
        f"已为当前会话绑定区服：{server}\n"
        "之后查询可不写区服；主动推送也按该区服发送。"
    )


def hint_push_need_bind(catalog: dict | None = None) -> str:
    bind = current_command_name(catalog, "绑定")
    return (
        "请先绑定区服后再打开推送。\n"
        f"发送：{bind} 区服名\n"
        f"例如：{bind} 梦江南"
    )


def hint_push_ok(kind: str, enabled: bool, catalog: dict | None = None, label: str = "") -> str:
    open_cmd = current_command_name(catalog, "打开")
    close_cmd = current_command_name(catalog, "关闭")
    notice = current_command_name(catalog, "通知管理")
    action = open_cmd if enabled else close_cmd
    name = label or kind
    return f"已为当前会话{action}{name}推送。发送 {notice} 可查看全部开关。"


def hint_need_token(catalog: dict | None = None) -> str:
    token_cmd = current_command_name(catalog, "Token")
    return (
        "该功能需要 JX3API 接口令牌，当前会话尚未配置。\n"
        "请前往 https://www.jx3api.com 购买接口令牌。\n"
        "\n"
        "配置方式（请私聊机器人，不要在群里发送接口令牌）：\n"
        "1. 在目标群聊发送 sid ，复制该群 UMO\n"
        f"2. 私聊发送：{token_cmd} <UMO> <你的接口令牌>\n"
        f"例如：{token_cmd} <UMO> <你的接口令牌>\n"
        "\n"
        "也可让机器人管理员在插件页面为该会话填写，或勾选「使用全局接口令牌」。"
    )


def hint_need_push_token(catalog: dict | None = None) -> str:
    token_cmd = current_command_name(catalog, "推送令牌")
    return (
        "该事件需要 JX3API 推送令牌，当前会话尚未配置，也未启用可用的全局推送令牌。\n"
        "免费事件档无需令牌；付费事件档请购买有效推送令牌。\n"
        "\n"
        "配置方式（请私聊机器人，不要在群里发送令牌）：\n"
        "1. 在目标群聊发送 sid，复制该群 UMO\n"
        f"2. 私聊发送：{token_cmd} <UMO> <你的推送令牌>\n"
        "\n"
        "也可让机器人管理员在插件页面为该会话填写，或勾选「使用全局推送令牌」。"
    )


def hint_need_ticket(catalog: dict | None = None) -> str:
    ticket_cmd = current_command_name(catalog, "推栏")
    return (
        "该功能需要推栏标识，当前未配置。\n"
        "推栏默认使用全局配置；如需本会话单独使用，请私聊机器人（不要在群里发送）：\n"
        "1. 在目标群聊发送 sid ，复制该群 UMO\n"
        f"2. 私聊发送：{ticket_cmd} <UMO> <你的推栏标识>\n"
        f"例如：{ticket_cmd} <UMO> <你的推栏标识>"
    )


def hint_group_secret() -> str:
    return (
        "请勿在群聊中发送 Token 或推栏标识。\n"
        "请先在目标群聊发送 sid 复制 UMO，再私聊机器人完成配置。"
    )


def hint_secret_saved(kind: str, umo: str) -> str:
    label = {
        "token": "接口令牌",
        "push_token": "推送令牌",
        "ticket": "推栏标识",
    }.get(kind, "密钥")
    return (
        f"已为会话 {umo} 保存 {label}。\n"
        f"该 {label} 仅用于该会话，不会在聊天中展示。"
    )


def hint_umo_invalid() -> str:
    return (
        "未找到该 UMO 对应的群聊会话。\n"
        "请先在目标群聊发送 sid ，复制完整 UMO 后再试。"
    )


def normalize_system_prefixes(system_prefixes=None) -> list[str]:
    prefixes = []
    for item in system_prefixes or ("/",):
        token = str(item or "").strip()
        if token and token not in prefixes:
            prefixes.append(token)
    return prefixes


def match_system_prefix(text: str, system_prefixes: list[str]) -> str:
    best = ""
    for token in system_prefixes:
        if text.startswith(token) and len(token) > len(best):
            best = token
    return best


def strip_command_prefix(
    text: str,
    enable: bool = False,
    prefix: str = "",
    system_prefixes=None,
) -> list[str] | None:
    text = (text or "").strip()
    if not text:
        return None
    prefixes = normalize_system_prefixes(system_prefixes)
    plugin_prefix = (prefix or "").strip()
    if enable:
        head = match_system_prefix(text, prefixes)
        if not head:
            return None
        body = text[len(head):].strip()
        if plugin_prefix:
            if not body.startswith(plugin_prefix):
                return None
            body = body[len(plugin_prefix):].strip()
        if not body:
            return None
        return body.split()
    head = match_system_prefix(text, prefixes)
    body = text[len(head):].strip() if head else text
    return body.split() if body else None



def hint_claim_ok(name: str) -> str:
    return f"已认领剑网3机器人。当前插件管理员：{name or '已记录'}"


def hint_private_only_claim(catalog: dict | None = None) -> str:
    claim = current_command_name(catalog, "认领")
    return f"{claim} 剑网3机器人 只能在私聊中发送。"


def hint_group_only_manage(catalog: dict | None = None) -> str:
    manager = current_command_name(catalog, "授权管理")
    viewer = current_command_name(catalog, "查看管理")
    remover = current_command_name(catalog, "删除管理")
    return f"{manager}、{viewer}、{remover} 只能在群聊中发送。"


def hint_need_claim(catalog: dict | None = None) -> str:
    claim = current_command_name(catalog, "认领")
    bind = current_command_name(catalog, "绑定")
    return (
        "该操作仅限 AstrBot 管理员或本会话认领人。\n"
        f"请先在私聊发送：{claim} 剑网3机器人\n"
        f"每个会话的认领人是第一个绑定成功的人；{bind} 区服名成功后才能成为该群认领人。"
    )


def hint_authorize_usage(catalog: dict | None = None) -> str:
    authorize = current_command_name(catalog, "授权管理")
    return f"用法：{authorize} @成员\n请直接 @ 需要授权的成员。"


def hint_deauthorize_usage(catalog: dict | None = None) -> str:
    deauthorize = current_command_name(catalog, "删除管理")
    return f"用法：{deauthorize} 序号\n例如：{deauthorize} 2"


def hint_list_admins_empty(catalog: dict | None = None) -> str:
    claim = current_command_name(catalog, "认领")
    return (
        "当前还没有插件管理员。\n"
        f"请先由 AstrBot 管理员发送：{claim} 剑网3机器人"
    )


def hint_claim_phrase(catalog: dict | None = None) -> str:
    claim = current_command_name(catalog, "认领")
    return f"用法：{claim} 剑网3机器人"


def format_command_error(cmd: str, error: BaseException, catalog: dict | None = None) -> str:
    detail = str(error or "").strip()
    if detail.startswith("缺少参数") or "required" in detail.lower():
        return hint_command_usage(cmd, catalog)
    if detail:
        return f"{hint_command_usage(cmd, catalog)}\n{detail}"
    return hint_command_usage(cmd, catalog)


def hint_unknown_server() -> str:
    return "请输入正确的区服。"


def hint_command_usage(cmd: str, catalog: dict | None = None) -> str:
    from .command_catalog import command_usage
    usage = command_usage(cmd, catalog)
    return f"请发送: 「 {usage} 」"

