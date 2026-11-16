"""排行榜单分类与可选值。

可选值与上游 JX3API `/rank/*` 的参数 enum 一致，新增榜单时同步这里即可。
条目格式：(显示名, 取数方式)。
"""

from __future__ import annotations

# 分类展示顺序
RANK_CATEGORY_ORDER: tuple[str, ...] = (
    "个人排行",
    "帮会排行",
    "绝境战场",
    "据点贡献",
    "江湖榜",
    "跨服名剑",
    "武林争霸",
    "决斗挑战",
)

# 取数方式 → jx3api 方法：name 走 rank_statistical，langke/bukuai 走各自社区榜，
# ladder/contest/wanted 走带 mode/camp 的专用方法。
RANK_CATEGORIES: dict[str, tuple[tuple[str, str], ...]] = {
    "个人排行": (
        ("老江湖五十强", "name"),
        ("庐园广记一百强", "name"),
        ("兵甲藏家五十强", "name"),
        ("薪火相传五十强", "name"),
        ("名师五十强", "name"),
        ("名士五十强", "name"),
        ("恶人后勤一百强", "name"),
        ("浩气后勤一百强", "name"),
        ("恶人英雄五十强", "name"),
        ("浩气英雄五十强", "name"),
        ("本周恶人一百强", "name"),
        ("本周浩气一百强", "name"),
    ),
    "帮会排行": (
        ("恶人神兵宝甲五十强", "name"),
        ("恶人爱心帮会五十强", "name"),
        ("浩气神兵宝甲五十强", "name"),
        ("浩气爱心帮会五十强", "name"),
        ("本周浩气五十强", "name"),
        ("本周恶人五十强", "name"),
        ("赛季浩气五十强", "name"),
        ("赛季恶人五十强", "name"),
        ("上周浩气五十强", "name"),
        ("上周恶人五十强", "name"),
    ),
    "绝境战场": (
        ("绝境名士录", "name"),
        ("龙门天命榜", "name"),
        ("荒漠霸王榜", "name"),
        ("独步尊者榜", "name"),
        ("喋血枭雄录", "name"),
        ("佛系圣手榜", "name"),
        ("瀚海兵甲榜", "name"),
    ),
    "据点贡献": (
        ("不空关", "name"),
        ("世外坡", "name"),
        ("凛风堡", "name"),
        ("凤鸣堡", "name"),
        ("千岩关", "name"),
        ("卧龙坡", "name"),
        ("啖杏林", "name"),
        ("大理山城", "name"),
        ("惊虬谷", "name"),
        ("扶风郡", "name"),
        ("日月崖", "name"),
        ("枫湖寨", "name"),
        ("武王城", "name"),
        ("澜沧城", "name"),
        ("激流坞", "name"),
        ("烈日岗", "name"),
        ("盘龙坞", "name"),
        ("神池岭", "name"),
        ("秋雨堡", "name"),
        ("红莲岗", "name"),
        ("逐鹿坪", "name"),
        ("金门关", "name"),
        ("霜戈堡", "name"),
        ("青云坞", "name"),
        ("飞沙关", "name"),
        ("龙门镇", "name"),
    ),
    "江湖榜": (
        ("江湖浪客榜", "langke"),
        ("捕快荣誉榜", "bukuai"),
    ),
    "跨服名剑": (
        ("2v2", "ladder"),
        ("3v3", "ladder"),
        ("5v5", "ladder"),
    ),
    "武林争霸": (
        ("浩气盟", "contest"),
        ("恶人谷", "contest"),
    ),
    "决斗挑战": (
        ("公开", "wanted"),
        ("私密", "wanted"),
    ),
}

# 显示名 → (分类, 取数方式)，供「直接发榜单名」匹配
RANK_NAME_INDEX: dict[str, tuple[str, str]] = {
    name: (category, kind)
    for category, entries in RANK_CATEGORIES.items()
    for name, kind in entries
}


def rank_entries(category: str) -> tuple[tuple[str, str], ...]:
    return RANK_CATEGORIES.get(category, ())


def match_rank_name(text: str) -> tuple[str, str] | None:
    """整串精确匹配榜单名，未命中返回 None。"""
    return RANK_NAME_INDEX.get(str(text or "").strip())
