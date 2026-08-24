from __future__ import annotations

from dataclasses import dataclass

UNBOUND_SERVER = "UNBOUND_SERVER"
CREDENTIAL_MISSING = "CREDENTIAL_MISSING"
GROUP_SECRET_FORBIDDEN = "group_secret_forbidden"
CLAIM_PHRASE = "剑网3机器人"

PUSH_TYPES = ("开服", "新闻", "刷马", "赤兔")
PUSH_FIELD = {
    "开服": "push_kaifu",
    "新闻": "push_xinwen",
    "刷马": "push_shuma",
    "赤兔": "push_chitu",
}

NEED_TICKET = frozenset({
    "战绩",
    "名剑排行",
    "名剑统计",
    "阵眼",
    "资历排行",
    "技能",
    "奇穴",
    "资历分布",
    "名片预设",
})

NEED_TOKEN = frozenset({
    "关隘", "赤兔", "本周赤兔", "阵营奉献", "烟花", "刷马", "马场",
    "战绩", "名剑排行", "名剑统计",
    "名士五十强", "老江湖五十强", "兵甲藏家五十强", "名师五十强",
    "阵营英雄五十强", "薪火相传五十强", "庐园广记一百强",
    "浩气神兵宝甲五十强", "恶人神兵宝甲五十强",
    "浩气爱心帮会五十强", "恶人爱心帮会五十强",
    "赛季恶人五十强", "赛季浩气五十强",
    "上周恶人五十强", "上周浩气五十强",
    "本周恶人五十强", "本周浩气五十强",
    "试炼排行", "阵营拍卖", "的卢", "金价", "物价", "成本", "看号", "诛恶",
    "名片", "全名片", "随机秀", "奇遇", "查询", "未出", "汇总", "近期", "统计",
    "精耐", "百战", "成就", "角色", "阵眼", "资历排行", "技能", "奇穴", "资历",
    "聊天", "骗子", "拜师", "收徒", "招募", "团长", "团牌",
    "贴吧物价", "818", "副本", "掉落",
    "跨服名剑", "武林争霸", "捕快", "浪客", "决斗",
    "资历分布", "外观搜索", "名片预设",
    "急速", "试炼秒伤", "试炼赛季",
})

# 命令最少需要的非服务器参数个数。少填了就把绑定服插到最前。
SERVER_ARITY = {
    "烟花": 1, "刷马": 0, "马场": 0, "战绩": 1,
    "名士五十强": 0, "老江湖五十强": 0, "兵甲藏家五十强": 0, "名师五十强": 0,
    "阵营英雄五十强": 0, "薪火相传五十强": 0, "庐园广记一百强": 0,
    "浩气神兵宝甲五十强": 0, "恶人神兵宝甲五十强": 0,
    "浩气爱心帮会五十强": 0, "恶人爱心帮会五十强": 0,
    "赛季恶人五十强": 0, "赛季浩气五十强": 0,
    "上周恶人五十强": 0, "上周浩气五十强": 0,
    "本周恶人五十强": 0, "本周浩气五十强": 0,
    "试炼排行": 1, "阵营拍卖": 0, "的卢": 0, "金价": 0, "成本": 1,
    "帮战": 0, "沙盘": 0, "诛恶": 0, "名片": 1, "全名片": 1, "随机秀": 0,
    "奇遇": 1, "查询": 1, "未出": 1, "汇总": 0, "近期": 0,
    "精耐": 1, "成就": 2, "角色": 1, "资历排行": 0, "聊天": 1, "统战": 0,
    "花价": 0, "拜师": 0, "收徒": 0, "招募": 0, "团长": 0, "团牌": 0,
    "开服": 0, "副本": 1, "资历": 1, "交易行": 1,
    "跨服名剑": 0, "武林争霸": 0, "捕快": 0, "浪客": 0, "决斗": 0,
    "资历分布": 1, "名片预设": 1,
}

SERVER_SECOND_COMMANDS = frozenset({
    "物价", "统计", "骗子", "贴吧物价", "掉落",
})


def mask_secret(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "未配置"
    if len(text) <= 4:
        return "已配置"
    return "****" + text[-4:]


def resolve_query_server(explicit: str, bound: str) -> str:
    server = (explicit or "").strip()
    if server:
        return server
    bound = (bound or "").strip()
    if bound:
        return bound
    return UNBOUND_SERVER


MODE_TOKENS = {"22", "33", "55", "2v2", "3v3", "5v5"}


SCHOOL_TAILS = {
    "万花", "纯阳", "七秀", "少林", "天策", "藏剑", "五毒", "唐门", "明教",
    "丐帮", "苍云", "长歌", "霸刀", "蓬莱", "凌雪", "衍天", "药宗", "刀宗",
    "无方", "灵素", "段氏",
}

def _is_optional_tail(cmd: str, value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    if cmd in {"战绩", "跨服名剑"} and text.lower() in MODE_TOKENS:
        return True
    if cmd == "武林争霸" and text in {"浩气", "恶人", "浩气盟", "恶人谷", "1", "2"}:
        return True
    if cmd == "决斗" and text in {"公开", "私密", "1", "2"}:
        return True
    if cmd in {"金价", "阵营拍卖", "近期", "汇总", "聊天", "资历分布"} and text.isdigit():
        return True
    if cmd == "阵营拍卖" and not text.isdigit():
        return True
    if cmd in {"随机秀", "资历排行"} and text in SCHOOL_TAILS:
        return True
    return False

def inject_server_args(cmd: str, args: list[str], bound: str, known_servers: set[str] | None = None) -> list[str] | str:
    bound = (bound or "").strip()
    args = list(args)

    if cmd in SERVER_ARITY:
        needed = SERVER_ARITY[cmd]
        core = list(args)
        tail = []
        while core and _is_optional_tail(cmd, core[-1]):
            tail.insert(0, core.pop())
        if len(core) <= needed:
            if not bound:
                return UNBOUND_SERVER
            return [bound] + core + tail
        return args

    if cmd in SERVER_SECOND_COMMANDS:
        if len(args) >= 2:
            return args
        if not bound:
            return UNBOUND_SERVER
        if len(args) == 1:
            return [args[0], bound]
        return UNBOUND_SERVER

    if cmd == "818":
        if not args:
            return [bound] + args if bound else args
        return args

    return args


@dataclass
class AdminCommand:
    action: str = ""
    target: str = ""
    value: str = ""
    error: str = ""


def parse_admin_command(parts: list[str], is_private: bool) -> AdminCommand:
    if not parts:
        return AdminCommand(error="empty")
    cmd = parts[0]
    if cmd in {"Token", "token", "推栏"}:
        if not is_private:
            return AdminCommand(error=GROUP_SECRET_FORBIDDEN)
        if len(parts) < 3:
            return AdminCommand(error="missing_secret_args")
        action = "set_token" if cmd.lower() == "token" else "set_ticket"
        return AdminCommand(action=action, target=parts[1], value=" ".join(parts[2:]).strip())
    if cmd == "认领":
        return AdminCommand(action="claim", value=" ".join(parts[1:]).strip())
    if cmd == "查询令牌":
        return AdminCommand(action="token_stats")
    if cmd == "绑定":
        if len(parts) < 2:
            return AdminCommand(error="missing_server")
        return AdminCommand(action="bind", value=" ".join(parts[1:]).strip())
    if cmd in {"打开", "关闭"}:
        if len(parts) < 2 or parts[1] not in PUSH_TYPES:
            return AdminCommand(error="missing_push_type")
        return AdminCommand(action="open_push" if cmd == "打开" else "close_push", value=parts[1])
    return AdminCommand(error="unknown")


def hint_unbound() -> str:
    return (
        "当前会话未绑定区服。\n"
        "请先由插件管理员发送：/绑定 区服名\n"
        "例如：/绑定 梦江南"
    )


def hint_bind_ok(server: str) -> str:
    return (
        f"已为当前会话绑定区服：{server}\n"
        "之后查询可不写区服；主动推送也按该区服发送。"
    )


def hint_bind_denied() -> str:
    return "绑定区服仅限插件管理员或 AstrBot 管理员。请先 /认领 剑网3机器人"


def hint_push_need_bind() -> str:
    return (
        "请先绑定区服后再打开推送。\n"
        "发送：/绑定 区服名\n"
        "例如：/绑定 梦江南"
    )


def hint_push_ok(kind: str, enabled: bool) -> str:
    action = "打开" if enabled else "关闭"
    return f"已为当前会话{action}{kind}推送。"


def hint_need_token() -> str:
    return (
        "该功能需要 JX3API Token，当前会话尚未配置。\n"
        "请前往 https://www.jx3api.com 购买 Token。\n"
        "\n"
        "配置方式（请私聊机器人，不要在群里发送 Token）：\n"
        "1. 在目标群发送 /sid ，复制该群 UMO\n"
        "2. 私聊发送：/Token <UMO> <你的Token>\n"
        "例如：/Token <UMO> <你的Token>\n"
        "\n"
        "也可让机器人管理员在插件页面为该会话填写，或勾选「使用全局 Token」。"
    )


def hint_need_ticket() -> str:
    return (
        "该功能需要推栏标识，当前未配置。\n"
        "推栏默认使用全局配置；如需本会话单独使用，请私聊机器人（不要在群里发送）：\n"
        "1. 在目标群发送 /sid ，复制该群 UMO\n"
        "2. 私聊发送：/推栏 <UMO> <你的推栏标识>\n"
        "例如：/推栏 <UMO> <你的推栏标识>"
    )


def hint_group_secret() -> str:
    return (
        "请勿在群聊中发送 Token 或推栏标识。\n"
        "请先在目标群发送 /sid 复制 UMO，再私聊机器人完成配置。"
    )


def hint_secret_saved(kind: str, umo: str) -> str:
    label = "Token" if kind == "token" else "推栏标识"
    return (
        f"已为会话 {umo} 保存 {label}。\n"
        f"该 {label} 仅用于该会话，不会在聊天中展示。"
    )


def hint_umo_invalid() -> str:
    return (
        "未找到该 UMO 对应的会话。\n"
        "请先在目标群或私聊发送 /sid ，复制完整 UMO 后再试。"
    )


def strip_command_prefix(text: str, enable: bool = False, prefix: str = "") -> list[str] | None:
    text = (text or "").strip()
    if not text:
        return None
    if enable:
        prefix = prefix or ""
        if prefix and text.startswith(prefix):
            text = text[len(prefix):].strip()
        elif text.startswith("/"):
            text = text[1:].strip()
        else:
            return None
    elif text.startswith("/"):
        text = text[1:].strip()
    return text.split() if text else None



def hint_claim_ok(name: str) -> str:
    return f"已认领剑网3机器人。当前插件管理员：{name or '已记录'}"


def hint_claim_taken(name: str) -> str:
    return f"该机器人已被认领。当前插件管理员：{name or '已记录'}"


def hint_need_claim() -> str:
    return (
        "绑定区服、打开推送、配置 Token/推栏仅限插件管理员。\n"
        "请先由 AstrBot 管理员或认领人发送：/认领 剑网3机器人"
    )


def hint_claim_phrase() -> str:
    return "用法：/认领 剑网3机器人"
