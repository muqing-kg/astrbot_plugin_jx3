import re
from typing import Any


PAGE_META_NONE: set[str] = set()


_PAGE_ROW_SELECTORS = {
    "data_list": ("rows", "groups[].items"),
    "diaoluo": ("items",),
    "juesheliaotian": ("list",),
    "mingjianpaihang": ("lists",),
    "mingjiantongji": ("items",),
    "rank_role": ("items",),
    "rank_tong0": ("items",),
    "rank_tong1": ("items",),
    "rank_tong2": ("items",),
    "shilianpaixing": ("items",),
    "shitu": ("items",),
    "tuanduizhaomu": ("list",),
    "yanhuan": ("list",),
    "zhanji": ("history",),
    "zilipaixing": ("items",),
}


def _meta_pick(payload: dict, *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _meta_mode_label(mode: Any) -> str:
    text = str(mode or "").strip().lower()
    if text in {"0", "2", "22", "2v2"}:
        return "2V2"
    if text in {"2", "5", "55", "5v5"}:
        return "5V5"
    return "3V3"


def _meta_update_time(payload: dict) -> str:
    return _meta_pick(payload, "update_time", "short_time")


def _meta_count(payload: dict, *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list) and value:
            return f"{len(value)} 条"
        if value not in (None, ""):
            return f"{value} 条"
    return ""


def _meta_join(*parts: Any) -> str:
    return " · ".join(str(part).strip() for part in parts if str(part or "").strip())


def build_page_meta(template: str, payload: dict) -> str:
    page_id = _page_id(template)
    filename = f"{page_id}.html" if page_id else ""
    if filename in PAGE_META_NONE:
        return ""

    server = _meta_pick(payload, "server", "serverName")
    role = _meta_pick(payload, "roleName", "role_name", "role", "name")
    mode = _meta_pick(payload, "mode")
    total = payload.get("total")
    items = payload.get("items") or payload.get("list") or payload.get("lists")
    item_count = len(items) if isinstance(items, list) else None
    update_time = _meta_update_time(payload)

    if filename == "notice.html":
        return _meta_join(_meta_pick(payload, "display_name"), server)

    if filename == "helps.html":
        return _meta_join(_meta_pick(payload, "display_name"), server)

    if filename == "baizhan.html":
        return _meta_join(
            _meta_pick(payload, "start"),
            _meta_pick(payload, "end"),
            update_time,
        )

    if filename in {
        "card_gallery.html", "juesheqiyu.html", "weizuoqiyu.html",
        "yanhuan.html", "jingnai.html", "chengjiu.html", "zili.html",
        "zhanji.html", "juesheliaotian.html",
    }:
        parts = [server, role]
        if filename == "zhanji.html" and mode:
            parts.append(f"{_meta_mode_label(mode)} 模式")
        if filename == "juesheliaotian.html" and total not in (None, ""):
            parts.append(f"{total} 条")
        return _meta_join(*parts)

    if filename in {
        "jinjia.html", "huajia.html", "jiaoyihang.html", "qiyuhuizong.html",
        "jinqiqiyu.html", "qiyuliebiao.html", "bangzhanjilu.html",
        "zhueevent.html", "dilujilu.html", "zhengyingpaimai.html",
        "tuanduizhaomu.html", "shitu.html", "diaoluo.html",
    }:
        parts = [server]
        if filename == "bangzhanjilu.html":
            match_count = payload.get("match_count") or item_count
            if match_count:
                parts.append(f"{match_count} 场")
            ongoing = payload.get("ongoing_count")
            if ongoing not in (None, ""):
                parts.append(f"进行中 {ongoing}")
            parts.append(update_time)
        elif filename == "shitu.html":
            parts.append(_meta_pick(payload, "title"))
            parts.append(_meta_pick(payload, "keyword"))
            if item_count:
                parts.append(f"{item_count} 人")
            parts.append(update_time)
        elif filename == "qiyuliebiao.html":
            parts.append(_meta_pick(payload, "qiyuname", "name"))
            parts.append(_meta_count(payload, "items"))
            parts.append(update_time)
        elif filename == "tuanduizhaomu.html":
            parts.append(_meta_pick(payload, "recruit_type"))
            parts.append(_meta_pick(payload, "keyword"))
            parts.append(_meta_count(payload, "list"))
            parts.append(update_time)
        elif filename == "huajia.html":
            parts.append(_meta_pick(payload, "flower_name", "name"))
            parts.append(_meta_pick(payload, "map_name"))
            parts.append(update_time)
        elif filename == "jiaoyihang.html":
            parts.append(_meta_pick(payload, "search_name", "name"))
            parts.append(_meta_count(payload, "list", "result_count"))
            parts.append(update_time)
        elif filename in {"diaoluo.html", "zhengyingpaimai.html"}:
            parts.append(_meta_pick(payload, "name", "item_name", "keyword"))
            parts.append(_meta_count(payload, "items", "list"))
            parts.append(update_time)
        else:
            if filename == "qiyuhuizong.html":
                num = payload.get("num")
                if num not in (None, ""):
                    parts.append(f"最近 {num} 天")
            parts.append(_meta_count(payload, "items", "list"))
            parts.append(update_time)
        return _meta_join(*parts)

    if filename in {"jineng.html", "qixue.html"}:
        return _meta_pick(payload, "name")

    if filename == "mingjiantongji.html":
        return _meta_join(
            _meta_pick(payload, "mode_label") or _meta_mode_label(_meta_pick(payload, "mode")),
            update_time,
        )

    if filename == "xiaoyao.html":
        return _meta_join(
            _meta_pick(payload, "xiaoyao_name") or "全部心法",
            update_time,
        )

    if filename == "xingxiashijian.html":
        return _meta_join(_meta_pick(payload, "name"), update_time)

    if filename == "shilianpaixing.html":
        return _meta_join(server, _meta_pick(payload, "name"), update_time)

    if filename in {"zhuangshi.html", "qiwu.html", "wujia.html", "chengbeng.html"}:
        return _meta_join(
            _meta_pick(payload, "name", "item_name"),
            server,
            update_time,
        )

    if filename == "mingjianpaihang.html":
        return _meta_join(
            "全服",
            "名剑排行",
            _meta_mode_label(_meta_pick(payload, "mode")),
            update_time,
        )

    if filename == "richangyuche.html":
        return _meta_join(_meta_pick(payload, "scope"), update_time)

    if filename == "qiyugonglue.html":
        return _meta_join(_meta_pick(payload, "qiyuname", "name"), update_time)

    if filename == "zilipaixing.html":
        return _meta_join(server, _meta_pick(payload, "school") or "资历排行", update_time)

    if filename == "rank_role.html" or filename.startswith("rank_"):
        rank_name = _meta_pick(payload, "rank_name")
        parts = [server]
        if "恶人" in rank_name:
            parts.append("恶人谷")
        elif "浩气" in rank_name:
            parts.append("浩气盟")
        parts.append(rank_name)
        parts.append(update_time)
        return _meta_join(*parts)

    if filename == "data_list.html":
        rank_name = _meta_pick(payload, "rank_name")
        if rank_name:
            mode_label = _meta_pick(payload, "mode_label")
            return _meta_join(server or "全服", rank_name, mode_label, update_time)
        if payload.get("groups"):
            return _meta_join(
                _meta_pick(payload, "server", "serverName"),
                _meta_pick(payload, "role_name", "roleName"),
                update_time,
            )
    return ""


def _page_id(template: str) -> str:
    match = re.search(r"<body[^>]*jx3-template--([a-z0-9_]+)", template or "")
    return match.group(1) if match else ""


def _limit_rows_at_selector(value: dict, selector: str, limit: int) -> bool:
    parts = selector.split(".")
    key, rest = parts[0], parts[1:]
    spread = key.endswith("[]")
    if spread:
        key = key[:-2]

    if not isinstance(value, dict) or key not in value:
        return False

    children = value[key]
    if spread:
        if not isinstance(children, (list, dict)):
            return False
        child_items = children if isinstance(children, list) else list(children.values())
    else:
        child_items = [children]

    if not rest:
        truncated = False
        for child in child_items:
            if isinstance(child, list) and len(child) > limit:
                child[:] = child[:limit]
                truncated = True
        return truncated

    return any(_limit_rows_at_selector(child, ".".join(rest), limit) for child in child_items)


def limit_image_rows(template: str, payload: dict, limit: int = 100) -> dict:
    """Limit known display rows for a page and mark shortened images."""
    if not isinstance(payload, dict) or payload.get("disable_row_limit"):
        return payload

    selectors = _PAGE_ROW_SELECTORS.get(_page_id(template), ())
    truncated = False
    for selector in selectors:
        truncated = _limit_rows_at_selector(payload, selector, limit) or truncated
    if truncated:
        payload["page_note"] = payload.get("page_note") or "仅展示前 100 条"
    return payload
