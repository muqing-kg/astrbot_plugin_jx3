import inspect
from pathlib import Path
from typing import cast

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
from astrbot.api import AstrBotConfig

from .core.sqlite import AsyncSQLiteDB
from .core.group_info import ensure_group_display_name
from .core.jx3api_data import JX3APIService
from .core.aijx3_data import AIJX3Service
from .core.jx3box_data import JX3BOXService
from .core.unua_data import UnuaService
from .core.async_task import AsyncTask
from .core.message import MessageBuilder
from .core.fun_basic import load_as_base64
from .core.session_store import CREDENTIAL_MISSING, SessionStore
from .core.session_policy import (
    GROUP_SECRET_FORBIDDEN,
    NEED_TICKET,
    NEED_TOKEN,
    PRIVATE_ONLY_COMMAND_IDS,
    UNBOUND_SERVER,
    UNKNOWN_SERVER,
    is_group_umo,
    CLAIM_PHRASE,
    resolve_display_name,
    hint_authorize_usage,
    hint_bind_ok,
    hint_claim_ok,
    hint_claim_phrase,
    hint_deauthorize_usage,
    hint_group_only_manage,
    hint_group_secret,
    hint_list_admins_empty,
    hint_need_claim,
    hint_private_only_claim,
    hint_need_ticket,
    hint_need_token,
    hint_need_push_token,
    hint_push_need_bind,
    hint_push_ok,
    hint_secret_saved,
    hint_umo_invalid,
    hint_unbound,
    hint_command_usage,
    inject_server_args,
    parse_admin_command,
    remap_admin_parts,
    current_command_name,
    format_command_error,
    hint_unknown_server,
    can_bind_session,
    is_astrbot_admin,
    normalize_system_prefixes,
    match_system_prefix,
    strip_command_prefix,
)
from .core.credentials import reset_request_credentials, set_request_credentials
from .core.mentions import mentioned_bot, mentioned_target, message_text_without_bot_mentions
from .core.page_api import SessionPageAPI
from .core.event_catalog import FREE_PUSH_ACTIONS, push_arg_map
from .core.command_catalog import apply_command_overrides, resolve_command, suggest_command
from .core.server_catalog import apply_alias_overrides, canonical_server
from .core.plugin_settings import PluginSettings


@register("astrbot_plugin_jx3",
          "muqing-kg",
          "聚合剑网三游戏数据，提供查询、图片渲染和后台推送。",
          "3.3.9",
          "https://github.com/muqing-kg/astrbot_plugin_jx3"
)
class Jx3ApiPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.conf = config
        self.prefix = self.conf.get("prefix", {}) or {}
        self.system_prefixes = self._load_system_prefixes()
        if self.prefix.get("enable"):
            logger.info(f"已启用指令前缀功能，前缀为：{self.prefix.get('text')}")
        else:
            logger.info("未启用插件指令前缀，走 AstrBot 默认前缀。")

        self.get_data_path()
        self.load_local_base64()
        self.create_all()
        self.command_map = {}
        logger.info("jx3api插件初始化完成")

    async def initialize(self):
        try:
            await self.local_sql_db.connect()
            await self.plugin_sql_db.connect()
            await self.init_achievement_cache_data()
            await self.sessions.init()
            await self.sessions.mark_astrbot_admin_claims(self._astrbot_admin_ids())
            await self.settings.init()
            self.command_catalog = apply_command_overrides(await self.settings.command_overrides())
            self.server_catalog = apply_alias_overrides(await self.settings.server_aliases())
            self.push_name_overrides = await self.settings.push_name_overrides()
            self.jx3api.push_names = dict(self.push_name_overrides)
            self.jx3api.command_catalog = self.command_catalog
            await self.jx3at.init_tasks()
            try:
                SessionPageAPI(self).register()
            except Exception as e:
                logger.warning(f"插件页面注册失败（不影响核心功能）: {e}")
        except Exception:
            if self.jx3at is not None:
                await self.jx3at.destroy()
            logger.exception("功能模块初始化失败")
            raise
        self.ini_command_map()
        logger.info("jx3api 异步插件初始化完成")

    async def terminate(self):
        for closer in (
            self.jx3at.destroy if self.jx3at else None,
            self.jx3api.close if self.jx3api else None,
            self.aijx3.close if self.aijx3 else None,
            self.jx3box.close if self.jx3box else None,
            self.local_sql_db.close if self.local_sql_db else None,
            self.plugin_sql_db.close if self.plugin_sql_db else None,
        ):
            if closer is None:
                continue
            try:
                await closer()
            except Exception:
                logger.exception("插件资源释放失败")
        logger.info("jx3api插件已卸载/停用")

    def get_data_path(self):
        self.local_data_dir = StarTools.get_data_dir("astrbot_plugin_jx3")
        self.plugin_data_dir = Path(__file__).parent / "data"
        self.plugin_temp_dir = Path(__file__).parent / "templates"
        self.local_data_path = self.local_data_dir / "local_data.db"
        self.plugin_data_path = self.plugin_data_dir / "plugin_data.db"
        self.plugin_temp_img = self.plugin_temp_dir / "img"
        self.plugin_temp_sect = self.plugin_temp_dir / "sect"
        self.plugin_temp_serendipity = self.plugin_temp_dir / "serendipity"

    def load_local_base64(self):
        self.icons = {
            "img": load_as_base64(str(self.plugin_temp_img)),
            "sect": load_as_base64(str(self.plugin_temp_sect)),
            "serendipity": load_as_base64(str(self.plugin_temp_serendipity)),
        }
        neutral = self.icons["img"].get("中立")
        if neutral:
            self.icons["sect"].setdefault("大侠", neutral)
            self.icons["sect"].setdefault("中立", neutral)

    def create_all(self):
        self.local_sql_db = AsyncSQLiteDB(str(self.local_data_path))
        self.plugin_sql_db = AsyncSQLiteDB(str(self.plugin_data_path))
        self.sessions = SessionStore(self.local_sql_db)
        self.jx3api = JX3APIService(self.conf, self.plugin_sql_db, self.local_sql_db)
        self.aijx3 = AIJX3Service(self.conf, self.plugin_sql_db, self.local_sql_db)
        self.jx3box = JX3BOXService(self.conf, self.plugin_sql_db, self.local_sql_db)
        self.unua = UnuaService()
        self.jx3at = AsyncTask(
            cast(Context, self.context),
            self.conf,
            self.jx3api,
            self.jx3box,
            self.sessions,
        )
        self.jx3cmd = MessageBuilder("", self.jx3api, self.aijx3, self.jx3box, self.unua, self.jx3at, self.icons)
        self.settings = PluginSettings(self.local_sql_db)
        self.command_catalog = apply_command_overrides({})
        self.server_catalog = apply_alias_overrides({})
        self.sessions.resolve_server = lambda name: canonical_server(self.server_catalog, name)

    async def init_achievement_cache_data(self):
        await self.local_sql_db.execute("""
        CREATE TABLE IF NOT EXISTS achievement_cache(
            key TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    def ini_command_map(self):
        self.command_map = {
            "功能": self.jx3cmd.helps,
            "通知管理": self.jx3cmd.notice_manage,
            "日常": self.jx3cmd.richang,
            "日常预测": self.jx3cmd.richangyuche,
            "穹野卫": self.jx3cmd.qiongyewei,
            "披风会": self.jx3cmd.pifenghui,
            "云从社": self.jx3cmd.yunchongshe,
            "楚天社": self.jx3cmd.chutianshe,
            "赤兔": self.jx3cmd.benrichitu,
            "本周赤兔": self.jx3cmd.benzhouchitu,
            "烟花": self.jx3cmd.yanhuachaxun,
            "刷马": self.jx3cmd.shuma,
            "马场": self.jx3cmd.machang,
            "战绩": self.jx3cmd.zhanji,
            "名剑排行": self.jx3cmd.mingjianpaihang,
            "名剑统计": self.jx3cmd.mingjiantongji,
            "名士排行": self.jx3cmd.mingshiwushiqiang,
            "江湖排行": self.jx3cmd.laojianghuwushiqiang,
            "兵甲排行": self.jx3cmd.bingjiacangjiawushiqiang,
            "名师排行": self.jx3cmd.mingshiwushiqiang_mentor,
            "阵营排行": self.jx3cmd.zhengyingyingxiongwushiqiang,
            "薪火排行": self.jx3cmd.xinhuoxiangchuanwushiqiang,
            "家园排行": self.jx3cmd.luyuanguangjiyibaiqiang,
            "浩气神兵排行": self.jx3cmd.haoqishenbingbaojiawushiqiang,
            "恶人神兵排行": self.jx3cmd.erenshenbingbaojiawushiqiang,
            "浩气爱心排行": self.jx3cmd.haoqiaixinbanghuiwushiqiang,
            "恶人爱心排行": self.jx3cmd.erenaixinbanghuiwushiqiang,
            "赛季恶人战功榜": self.jx3cmd.saijierenwushiqiang,
            "赛季浩气战功榜": self.jx3cmd.saijihaoqiwushiqiang,
            "上周恶人战功榜": self.jx3cmd.shangzhouerenwushiqiang,
            "上周浩气战功榜": self.jx3cmd.shangzhouhaoqiwushiqiang,
            "本周恶人战功榜": self.jx3cmd.benzhouerenwushiqiang,
            "本周浩气战功榜": self.jx3cmd.benzhouhaoqiwushiqiang,
            "试炼之地排行": self.jx3cmd.shilianpaixing,
            "跨服名剑榜": self.jx3cmd.kuafumingjian,
            "武林争霸赛": self.jx3cmd.wulinzhengba,
            "捕快荣誉榜": self.jx3cmd.bukuai,
            "江湖浪客榜": self.jx3cmd.langke,
            "决斗挑战榜": self.jx3cmd.juedou,
            "资历分布": self.jx3cmd.zilifenbu,
            "外观搜索": self.jx3cmd.waiguansousuo,
            "阵营拍卖": self.jx3cmd.zhengyingpaimai,
            "的卢拍卖": self.jx3cmd.dilujilu,
            "金价": self.jx3cmd.jinjia,
            "物价": self.jx3cmd.wujia,
            "配方": self.jx3cmd.chengbeng,
            "万宝楼": self.jx3cmd.kanhao,
            "帮战": self.jx3cmd.bangzhanjilu,
            "沙盘": self.jx3cmd.shapan,
            "诛恶": self.jx3cmd.zhueevent,
            "名片": self.jx3cmd.jueshemingpian,
            "全部名片": self.jx3cmd.shuoyoumingpian,
            "随机名片": self.jx3cmd.shuijimingpian,
            "查询": self.jx3cmd.juesheqiyu,
            "未出": self.jx3cmd.weizuoqiyu,
            "汇总": self.jx3cmd.qiyuhuizong,
            "近期": self.jx3cmd.jinqiqiyu,
            "统计": self.jx3cmd.qiyutongji,
            "攻略": self.jx3cmd.qiyugonglue,
            "精耐": self.jx3cmd.jingnai,
            "百战": self.jx3cmd.baizhan,
            "成就": self.jx3cmd.chengjiu,
            "角色": self.jx3cmd.jueshe,
            "在线": self.jx3cmd.unua_online,
            "属性": self.jx3cmd.unua_attribute,
            "阵眼": self.jx3cmd.zhenyan,
            "配装": self.jx3cmd.peizhuang,
            "资历排行": self.jx3cmd.zilipaixing,
            "技能": self.jx3cmd.jineng,
            "奇穴": self.jx3cmd.qixue,
            "聊天": self.jx3cmd.liaotian,
            "统战": self.jx3cmd.tongzhanyy,
            "小药": self.jx3cmd.xiaoyao,
            "花价": self.jx3cmd.huajia,
            "装饰": self.jx3cmd.zhuangshi,
            "器物谱": self.jx3cmd.qiwu,
            "拜师": self.jx3cmd.baishi,
            "收徒": self.jx3cmd.shoutu,
            "维护": self.jx3cmd.weihu,
            "新闻": self.jx3cmd.xinwen,
            "招募": self.jx3cmd.tuanduizhaomu,
            "团长": self.jx3cmd.tuanzhang,
            "团牌": self.jx3cmd.tuanpai,
            "答案之书": self.jx3cmd.daanzhishu,
            "舔狗语录": self.jx3cmd.tiangou,
            "喝什么": self.jx3cmd.heshengme,
            "吃什么": self.jx3cmd.chishengme,
            "骚话": self.jx3cmd.shaohua,
            "渣男语录": self.jx3cmd.zhananyulu,
            "科举": self.jx3cmd.keju,
            "开服": self.jx3cmd.kaifu,
            "技改": self.jx3cmd.jigai,
            "掉落": self.jx3cmd.diaoluo,
            "宏": self.jx3cmd.hong,
            "资历": self.jx3cmd.zili,
            "交易行": self.jx3cmd.jiaoyihang,
        }

    def parse_message(self, text: str) -> list[str] | None:
        return strip_command_prefix(
            text,
            bool(self.prefix.get("enable")),
            self.prefix.get("text") or "",
            self.system_prefixes,
        )

    def _looks_like_command(self, text: str) -> bool:
        text = str(text or "").strip()
        if not text:
            return False
        head = match_system_prefix(text, self.system_prefixes)
        if not head:
            return False
        body = text[len(head):].strip()
        if not body:
            return False
        plugin_prefix = (self.prefix.get("text") or "").strip()
        if plugin_prefix:
            return body.startswith(plugin_prefix)
        return True

    def _load_system_prefixes(self) -> list[str]:
        try:
            config = getattr(self.context, "astrbot_config", None) or {}
            raw = config.get("wake_prefix")
        except Exception:
            raw = None
        return normalize_system_prefixes(raw)

    def _astrbot_admin_ids(self) -> list[str]:
        try:
            config = getattr(self.context, "astrbot_config", None) or {}
            raw = config.get("admins_id", [])
        except Exception:
            raw = []
        if isinstance(raw, str):
            values = raw.replace("，", ",").split(",")
        elif isinstance(raw, (list, tuple, set)):
            values = list(raw)
        else:
            values = []
        result = []
        for value in values:
            identity = str(value or "").strip()
            if identity and identity not in result:
                result.append(identity)
        return result

    def _event_umo(self, event: AstrMessageEvent) -> str:
        try:
            return str(event.unified_msg_origin or "").strip()
        except Exception:
            return ""

    def _sender_name(self, event: AstrMessageEvent) -> str:
        try:
            if hasattr(event, "get_sender_name") and callable(event.get_sender_name):
                name = str(event.get_sender_name() or "").strip()
                if name:
                    return name
        except Exception:
            pass
        try:
            message_obj = getattr(event, "message_obj", None)
            if message_obj:
                for owner in (getattr(message_obj, "user", None), getattr(message_obj, "sender", None)):
                    if owner is None:
                        continue
                    for attr in ("nickname", "card", "name", "user_name"):
                        value = getattr(owner, attr, None)
                        if value not in (None, ""):
                            return str(value).strip()
        except Exception:
            pass
        return self._sender_id(event)

    @staticmethod
    def _valid_display_name(value: object) -> bool:
        return valid_display_name(value)

    def _group_display_name(self, event: AstrMessageEvent) -> str:
        try:
            if hasattr(event, "get_group_name") and callable(event.get_group_name):
                name = str(event.get_group_name() or "").strip()
                if self._valid_display_name(name):
                    return name
        except Exception:
            pass
        try:
            message_obj = getattr(event, "message_obj", None)
            if message_obj:
                group = getattr(message_obj, "group", None)
                if group:
                    for attr in ("group_name", "name", "nickname"):
                        value = getattr(group, attr, None)
                        if self._valid_display_name(value):
                            return str(value).strip()
        except Exception:
            pass
        return ""

    def _event_display_name(self, event: AstrMessageEvent, fallback: object = "") -> str:
        try:
            group_id = str(event.get_group_id() or "").strip()
            if group_id:
                return resolve_display_name(
                    self._group_display_name(event),
                    fallback,
                    group_id,
                )
            sender = str(event.get_sender_id() or "").strip()
            name = self._sender_name(event)
            if name and name != sender:
                return name
            return f"私聊 {sender}" if sender else ""
        except Exception:
            return ""

    def _is_private(self, event: AstrMessageEvent) -> bool:
        try:
            if hasattr(event, "is_private_chat") and callable(event.is_private_chat):
                return bool(event.is_private_chat())
        except Exception:
            pass
        try:
            return not bool(event.get_group_id())
        except Exception:
            return False

    def _sender_id(self, event: AstrMessageEvent) -> str:
        try:
            return str(event.get_sender_id() or "").strip()
        except Exception:
            return ""

    def _is_astrbot_admin(self, event: AstrMessageEvent) -> bool:
        try:
            event_is_admin = bool(hasattr(event, "is_admin") and callable(event.is_admin) and event.is_admin())
        except Exception:
            event_is_admin = False
        return is_astrbot_admin(event_is_admin, self._sender_id(event), self._astrbot_admin_ids())

    async def _is_session_owner_admin(self, event: AstrMessageEvent, umo: str = "") -> bool:
        if self._is_astrbot_admin(event):
            return True
        umo = umo or self._event_umo(event)
        return await self.sessions.is_session_owner(
            umo,
            self._sender_id(event),
            self._sender_name(event),
        )

    async def _is_plugin_admin(self, event: AstrMessageEvent, umo: str = "") -> bool:
        if self._is_astrbot_admin(event):
            return True
        umo = umo or self._event_umo(event)
        return await self.sessions.is_manager(
            umo,
            self._sender_id(event),
            self._sender_name(event),
        )

    def _global_token(self) -> str:
        return str(self.conf.get("jx3api_token", "") or "").strip()

    def _global_ticket(self) -> str:
        return str(self.conf.get("jx3api_ticket", "") or "").strip()

    def _global_push_token(self) -> str:
        return str(
            self.conf.get("jx3api_push_token", "")
            or self.conf.get("jx3api_ws_token", "")
            or ""
        ).strip()

    async def _handle_admin_command(self, event: AstrMessageEvent, parts: list[str]):
        parsed = parse_admin_command(
            remap_admin_parts(parts, self.command_catalog),
            is_private=self._is_private(event),
            push_args=push_arg_map(getattr(self, "push_name_overrides", {}) or {}),
        )
        if parsed.error == GROUP_SECRET_FORBIDDEN:
            return event.plain_result(hint_group_secret())
        if parsed.error == "claim_private_only":
            return event.plain_result(hint_private_only_claim(self.command_catalog))
        if parsed.error == "group_manage_only":
            return event.plain_result(hint_group_only_manage(self.command_catalog))
        if parsed.error == "missing_server":
            bind = current_command_name(self.command_catalog, "绑定")
            return event.plain_result(f"用法：{bind} 区服名\n例如：{bind} 梦江南")
        if parsed.error == "missing_push_type":
            open_cmd = current_command_name(self.command_catalog, "打开")
            close_cmd = current_command_name(self.command_catalog, "关闭")
            notice = current_command_name(self.command_catalog, "通知管理")
            return event.plain_result(f"用法：{open_cmd} 事件类型 或 {close_cmd} 事件类型\n发送 {notice} 查看全部事件类型")
        if parsed.error == "missing_secret_args":
            token_cmd = current_command_name(self.command_catalog, "Token")
            ticket_cmd = current_command_name(self.command_catalog, "推栏")
            return event.plain_result(f"用法：{token_cmd} <UMO> <接口令牌> 或 {ticket_cmd} <UMO> <推栏标识>")
        if parsed.error == "missing_authorize_target":
            return event.plain_result(hint_authorize_usage(self.command_catalog))
        if parsed.error == "missing_manager_index":
            return event.plain_result(hint_deauthorize_usage(self.command_catalog))
        if parsed.error:
            return None

        if parsed.action == "claim":
            if parsed.value != CLAIM_PHRASE:
                return event.plain_result(hint_claim_phrase(self.command_catalog))
            ok, name = await self.sessions.claim_admin(self._sender_id(event), self._sender_name(event))
            if not ok:
                return event.plain_result(hint_claim_phrase(self.command_catalog))
            return event.plain_result(hint_claim_ok(name))

        if parsed.action == "llm_enabled":
            if not await self._is_plugin_admin(event, umo=self._event_umo(event)):
                return event.plain_result(hint_need_claim(self.command_catalog))
            enabled = parsed.value == "1"
            await self.sessions.set_llm_enabled(self._event_umo(event), enabled)
            label = "张嘴" if enabled else "闭嘴"
            state = "允许" if enabled else "禁止"
            return event.plain_result(f"已{label}：被 @ 后{state}触发 LLM 回话。")

        if parsed.action in {"authorize", "deauthorize", "list_admins"}:
            if not await self._is_session_owner_admin(event):
                return event.plain_result(hint_need_claim(self.command_catalog))
            umo = self._event_umo(event)
            if parsed.action == "authorize":
                uid, name = mentioned_target(event)
                if not uid and not name:
                    return event.plain_result(hint_authorize_usage(self.command_catalog))
                ok, msg = await self.sessions.add_manager(umo, uid, name)
                if not ok:
                    return event.plain_result(msg)
                viewer = current_command_name(self.command_catalog, "查看管理")
                return event.plain_result(f"已授权管理员：{name or uid}\n发送 {viewer} 可查看当前管理员列表。")
            if parsed.action == "deauthorize":
                ok, msg = await self.sessions.remove_manager(umo, parsed.value)
                return event.plain_result(msg)
            snapshot = await self.sessions.manager_snapshot(umo)
            if not snapshot:
                return event.plain_result(hint_list_admins_empty(self.command_catalog))
            manager_row = await self.sessions.get(umo)
            return await self.jx3cmd.T2I_image_msg(
                event,
                lambda: self.jx3api.view_managers(
                    self._event_display_name(event, (manager_row or {}).get("display_name")),
                    snapshot,
                ),
            )

        if parsed.action == "token_stats":
            umo = self._event_umo(event)
            if not await self._is_plugin_admin(event, umo=umo):
                return event.plain_result(hint_need_claim(self.command_catalog))
            row = await self.sessions.get(umo)
            session_token = ((row or {}).get("token") or "").strip()
            global_token = self._global_token()
            use_global = bool((row or {}).get("use_global_token"))
            blocks = []
            if session_token:
                data = await self.jx3api.token_stats(session_token)
                title = "【该群接口令牌】"
                body = data.get("data") if data.get("code") == 200 else (data.get("msg") or "查询失败")
                blocks.append(title + "\n" + body)
            if use_global and global_token and global_token != session_token:
                data = await self.jx3api.token_stats(global_token)
                body = data.get("data") if data.get("code") == 200 else (data.get("msg") or "查询失败")
                blocks.append("【全局接口令牌】\n" + body)
            if not blocks:
                return event.plain_result(hint_need_token(self.command_catalog))
            return event.plain_result("\n\n".join(blocks))

        if parsed.action == "push_token_stats":
            umo = self._event_umo(event)
            if not await self._is_plugin_admin(event, umo=umo):
                return event.plain_result(hint_need_claim(self.command_catalog))
            row = await self.sessions.get(umo)
            group_push_token = ((row or {}).get("push_token") or "").strip()
            global_push_token = self._global_push_token()
            use_global_push_token = bool((row or {}).get("use_global_push_token"))
            blocks = []
            for label, value in (
                ("【该群推送令牌】", group_push_token),
                ("【全局推送令牌】", global_push_token if use_global_push_token else ""),
            ):
                if not value:
                    continue
                for index, token in enumerate([item.strip() for item in value.replace("，", ",").split(",") if item.strip()], 1):
                    suffix = f"（第 {index} 个）" if "," in value else ""
                    data = await self.jx3api.token_stats(token)
                    body = data.get("data") if data.get("code") == 200 else (data.get("msg") or "查询失败")
                    blocks.append(f"{label}{suffix}\n{body}")
            if not blocks:
                return event.plain_result(hint_need_push_token(self.command_catalog))
            return event.plain_result("\n\n".join(blocks))

        if parsed.action == "bind":
            umo = self._event_umo(event)
            current = await self.sessions.get(umo)
            if not can_bind_session(
                self._is_astrbot_admin(event),
                (current or {}).get("claim_identity"),
                self._sender_id(event),
            ):
                return event.plain_result(hint_need_claim(self.command_catalog))
            official = canonical_server(self.server_catalog, parsed.value)
            if not official:
                return event.plain_result("未识别的区服。请使用正式区服名或已配置的别名。")
            await self.sessions.bind_server(
                umo,
                official,
                self._event_display_name(event, (current or {}).get("display_name")),
                is_private=self._is_private(event),
            )
            if self._is_astrbot_admin(event):
                await self.sessions.set_session_claim(
                    umo,
                    self._sender_id(event),
                    self._sender_name(event),
                    claim_type="astrbot_admin",
                    force=True,
                )
            else:
                await self.sessions.set_session_claim(
                    umo,
                    self._sender_id(event),
                    self._sender_name(event),
                    claim_type="claimant",
                )
            return event.plain_result(hint_bind_ok(official))

        if parsed.action in {"open_push", "close_push"}:
            umo = self._event_umo(event)
            if not await self._is_plugin_admin(event, umo=umo):
                return event.plain_result(hint_need_claim(self.command_catalog))
            await self.sessions.ensure(
                umo,
                self._event_display_name(event),
                is_private=self._is_private(event),
            )
            row = await self.sessions.get(umo)
            if parsed.action == "open_push" and parsed.value not in FREE_PUSH_ACTIONS:
                push_token = self.sessions.resolve_push_token(row, self._global_push_token())
                if push_token == CREDENTIAL_MISSING:
                    return event.plain_result(hint_need_push_token(self.command_catalog))
                stats = await self.jx3api.token_stats(push_token)
                if stats.get("code") != 200 or stats.get("valid") is False:
                    detail = str(stats.get("msg") or "推送令牌不可用")
                    if "过期" in detail:
                        detail = "JX3API 推送令牌已过期，请更换或续费后再试。"
                    elif any(key in detail for key in ("次数", "余额", "额度", "不足", "用尽")):
                        detail = "JX3API 推送令牌次数已用尽，请更换或续费后再试。"
                    return event.plain_result(f"推送令牌校验失败：{detail}")
            ok, msg = await self.sessions.set_push(umo, parsed.value, parsed.action == "open_push")
            if not ok:
                return event.plain_result(hint_push_need_bind(self.command_catalog))
            await self.jx3at.refresh_jobs()
            return event.plain_result(hint_push_ok(
                parsed.value,
                parsed.action == "open_push",
                self.command_catalog,
                label=parsed.label,
            ))

        if parsed.action in {"set_token", "set_ticket"}:
            target = parsed.target.strip()
            if not is_group_umo(target):
                return event.plain_result("目标 UMO 必须是群聊会话。请先在目标群发送 sid 复制 UMO。")
            row = await self.sessions.get(target)
            if not row:
                return event.plain_result(hint_umo_invalid())
            values = [part.strip() for part in parsed.value.replace("，", ",").split(",") if part.strip()]
            if not values:
                label = "接口令牌" if parsed.action == "set_token" else "推栏标识"
                return event.plain_result(f"请填写需要保存的 {label}。")
            if parsed.action == "set_token":
                for index, value in enumerate(values, 1):
                    data = await self.jx3api.token_stats(value)
                    if data.get("code") != 200 or data.get("valid") is False:
                        detail = str(data.get("msg") or "接口令牌不可用")
                        if "过期" in detail:
                            detail = "JX3API 接口令牌已过期，请更换后再试。"
                        elif any(key in detail for key in ("次数", "余额", "额度", "不足", "用尽")):
                            detail = "JX3API 接口令牌次数已用尽，请更换或续费后再试。"
                        return event.plain_result(f"第 {index} 个接口令牌校验失败：{detail}")
                await self.sessions.set_token(target, parsed.value)
                return event.plain_result(hint_secret_saved("token", target) + "\n已通过 JX3API 校验。")
            probe_token = self.sessions.resolve_token(row, self._global_token())
            if probe_token == CREDENTIAL_MISSING:
                probe_token = ""
            elif "," in probe_token:
                probe_token = probe_token.split(",", 1)[0].strip()
            for index, value in enumerate(values, 1):
                ok, msg = await self.jx3api.validate_ticket(value, probe_token)
                if not ok:
                    return event.plain_result(f"第 {index} 个推栏标识校验失败：{msg}")
            await self.sessions.set_ticket(target, parsed.value)
            return event.plain_result(hint_secret_saved("ticket", target) + "\n已通过真实接口校验。")
        if parsed.action == "set_push_token":
            target = parsed.target.strip()
            if not is_group_umo(target):
                return event.plain_result("目标 UMO 必须是群聊会话。请先在目标群发送 sid 复制 UMO。")
            row = await self.sessions.get(target)
            if not row:
                return event.plain_result(hint_umo_invalid())
            values = [part.strip() for part in parsed.value.replace("，", ",").split(",") if part.strip()]
            if not values:
                return event.plain_result("请填写需要保存的推送令牌。")
            if len(values) > 1:
                return event.plain_result("推送令牌一次只能配置一枚；如需更换，请保存新的推送令牌。")
            for index, value in enumerate(values, 1):
                data = await self.jx3api.token_stats(value)
                if data.get("code") != 200 or data.get("valid") is False:
                    detail = str(data.get("msg") or "推送令牌不可用")
                    if "过期" in detail:
                        detail = "JX3API 推送令牌已过期，请更换后再试。"
                    elif any(key in detail for key in ("次数", "余额", "额度", "不足", "用尽")):
                        detail = "JX3API 推送令牌次数已用尽，请更换或续费后再试。"
                    return event.plain_result(f"第 {index} 个推送令牌校验失败：{detail}")
            await self.sessions.set_push_token(target, parsed.value)
            await self.jx3at.refresh_jobs()
            return event.plain_result(hint_secret_saved("push_token", target) + "\n已通过 JX3API 校验。")
        return None

    async def _call_with_auto_args(self, handler, event: AstrMessageEvent, args: list[str]):
        sig = inspect.signature(handler)
        params = list(sig.parameters.values())
        call_args = []
        arg_index = 0
        for p in params:
            if p.name == "self":
                continue
            if p.name == "event":
                call_args.append(event)
                continue
            if arg_index < len(args):
                raw = args[arg_index]
                arg_index += 1
                try:
                    if p.annotation is int:
                        call_args.append(int(raw))
                    elif p.annotation is float:
                        call_args.append(float(raw))
                    else:
                        call_args.append(raw)
                except Exception:
                    call_args.append(p.default)
            else:
                if p.default is not inspect._empty:
                    call_args.append(p.default)
                else:
                    raise ValueError(f"缺少参数: {p.name}")
        return await handler(*call_args)

    async def _run_menu_choice(
        self,
        event: AstrMessageEvent,
        choice: int,
        ids: tuple[str, ...],
        args: list[str],
    ):
        if choice < 1 or choice > len(ids):
            await event.send(event.plain_result("无效序号，结束会话"))
            return
        result = await self._exec_menu_command(event, ids[choice - 1], list(args))
        if result is not None:
            await event.send(result)

    async def _exec_menu_command(
        self,
        event: AstrMessageEvent,
        cmd_id: str,
        args: list[str],
    ):
        handler = self.command_map.get(cmd_id)
        if not handler:
            return event.plain_result(f"该功能暂不可用：{cmd_id}")

        row = await self.sessions.ensure(
            self._event_umo(event),
            self._event_display_name(event),
            is_private=self._is_private(event),
        )
        bound = (row.get("server") or "").strip()
        injected = inject_server_args(
            cmd_id,
            args,
            bound,
            resolver=lambda name: canonical_server(self.server_catalog, name),
        )
        if injected == UNBOUND_SERVER:
            return event.plain_result(hint_unbound(self.command_catalog))
        if injected == UNKNOWN_SERVER:
            return event.plain_result(hint_unknown_server())
        args = injected

        if cmd_id in NEED_TOKEN:
            token = self.sessions.resolve_token(row, self._global_token())
            if token == CREDENTIAL_MISSING:
                return event.plain_result(hint_need_token(self.command_catalog))
        else:
            token = self.sessions.resolve_token(row, self._global_token())
            if token == CREDENTIAL_MISSING:
                token = ""

        if cmd_id in NEED_TICKET:
            ticket = self.sessions.resolve_ticket(row, self._global_ticket())
            if ticket == CREDENTIAL_MISSING:
                return event.plain_result(hint_need_ticket(self.command_catalog))
        else:
            ticket = self.sessions.resolve_ticket(row, self._global_ticket())
            if ticket == CREDENTIAL_MISSING:
                ticket = ""

        creds = set_request_credentials(token or None, ticket or None)
        try:
            return await self._call_with_auto_args(handler, event, args)
        except Exception as e:
            logger.exception(f"菜单子命令执行失败: {cmd_id}, error={e}")
            return event.plain_result(format_command_error(cmd_id, e, self.command_catalog))
        finally:
            reset_request_credentials(creds)

    async def _cmd_ranking(self, event: AstrMessageEvent, args: list[str]):
        ids = self.jx3cmd.RANKING_IDS
        async def runner(choice: int, reply_event: AstrMessageEvent):
            await self._run_menu_choice(reply_event, choice, ids, [])
        await self.jx3cmd.send_command_menu(event, "排行榜", ids, runner)

    async def _cmd_zhangong(self, event: AstrMessageEvent, args: list[str]):
        camp = (args[0] if args else "").strip()
        if camp in {"恶人", "恶人谷"}:
            ids = self.jx3cmd.ZHANGONG_EWE
        elif camp in {"浩气", "浩气盟"}:
            ids = self.jx3cmd.ZHANGONG_HAO
        elif camp:
            return event.plain_result(hint_command_usage("战功榜", self.command_catalog))
        else:
            ids = self.jx3cmd.ZHANGONG_ALL
        async def runner(choice: int, reply_event: AstrMessageEvent):
            await self._run_menu_choice(reply_event, choice, ids, [])
        await self.jx3cmd.send_command_menu(event, "战功榜", ids, runner)

    async def _cmd_card(self, event: AstrMessageEvent, args: list[str]):
        if not args:
            return event.plain_result(hint_command_usage("名片", self.command_catalog))
        ids = self.jx3cmd.CARD_IDS
        async def runner(choice: int, reply_event: AstrMessageEvent):
            await self._run_menu_choice(reply_event, choice, ids, list(args))
        await self.jx3cmd.send_command_menu(event, "名片", ids, runner)

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        if not self.command_map:
            return
        bot_at = mentioned_bot(event)
        clean_text = message_text_without_bot_mentions(event)
        parts = self.parse_message(clean_text)
        if self._is_private(event):
            if not parts:
                return
            normalized = remap_admin_parts(parts, self.command_catalog)
            trigger = normalized[0]
            if trigger.lower() == "token":
                trigger = "Token"
            if trigger not in PRIVATE_ONLY_COMMAND_IDS:
                return
            admin_ret = await self._handle_admin_command(event, parts)
            if admin_ret is not None:
                event.stop_event()
                yield admin_ret
            return
        if not parts:
            if bot_at:
                row = await self.sessions.ensure(
                    self._event_umo(event),
                    self._event_display_name(event),
                    is_private=self._is_private(event),
                )
                if self.sessions.is_llm_enabled(row):
                    yield self._forced_llm(event, clean_text)
            return

        umo = self._event_umo(event)
        row = await self.sessions.ensure(
            umo,
            self._event_display_name(event),
            is_private=self._is_private(event),
        )
        row = await ensure_group_display_name(self.context, self.sessions, umo, row)
        if self._is_astrbot_admin(event):
            await self.sessions.reconcile_astrbot_admin_session(
                umo,
                self._sender_id(event),
                self._sender_name(event),
            )
            row = await self.sessions.get(umo) or row
        claim_cmd = ((self.command_catalog.get("认领") or {}).get("command") or "认领")
        claim_and_voice_cmds = {claim_cmd, current_command_name(self.command_catalog, "张嘴"), current_command_name(self.command_catalog, "闭嘴")}
        if (
            not self.sessions.is_bot_enabled(row)
            and not bot_at
            and parts[0] not in claim_and_voice_cmds
        ):
            return

        admin_ret = await self._handle_admin_command(event, parts)
        if admin_ret is not None:
            event.stop_event()
            yield admin_ret
            return

        trigger, *args = parts
        cmd = resolve_command(self.command_catalog, trigger)
        if not cmd:
            if bot_at:
                if self.sessions.is_llm_enabled(row):
                    yield self._forced_llm(event, clean_text)
                return
            if self._looks_like_command(event.message_str):
                suggested = suggest_command(self.command_catalog, trigger)
                if suggested:
                    event.stop_event()
                    yield event.plain_result(hint_command_usage(suggested, self.command_catalog))
                    return
            return

        if cmd in {"排行榜", "战功榜"}:
            event.stop_event()
            if cmd == "排行榜":
                yield await self._cmd_ranking(event, args)
            else:
                yield await self._cmd_zhangong(event, args)
            return
        if cmd == "通知管理":
            event.stop_event()
            yield await self.jx3cmd.notice_manage(
                event,
                display_name=self._event_display_name(event, row.get("display_name")),
                server=(row.get("server") or "").strip() or "未绑定",
                enabled=await self.sessions.enabled_actions(umo),
            )
            return
        if cmd == "功能":
            event.stop_event()
            yield await self.jx3cmd.helps(
                event,
                display_name=self._event_display_name(event, row.get("display_name")),
                server=(row.get("server") or "").strip(),
            )
            return

        handler = self.command_map.get(cmd)
        if not handler:
            return

        bound = (row.get("server") or "").strip()
        injected = inject_server_args(
            cmd,
            args,
            bound,
            resolver=lambda name: canonical_server(self.server_catalog, name),
        )
        if injected == UNBOUND_SERVER:
            event.stop_event()
            yield event.plain_result(hint_unbound(self.command_catalog))
            return
        if injected == UNKNOWN_SERVER:
            event.stop_event()
            yield event.plain_result(hint_unknown_server())
            return
        args = injected

        if cmd in NEED_TOKEN:
            token = self.sessions.resolve_token(row, self._global_token())
            if token == CREDENTIAL_MISSING:
                event.stop_event()
                yield event.plain_result(hint_need_token(self.command_catalog))
                return
        else:
            token = self.sessions.resolve_token(row, self._global_token())
            if token == CREDENTIAL_MISSING:
                token = ""

        if cmd in NEED_TICKET:
            ticket = self.sessions.resolve_ticket(row, self._global_ticket())
            if ticket == CREDENTIAL_MISSING:
                event.stop_event()
                yield event.plain_result(hint_need_ticket(self.command_catalog))
                return
        else:
            ticket = self.sessions.resolve_ticket(row, self._global_ticket())
            if ticket == CREDENTIAL_MISSING:
                ticket = ""

        if cmd == "名片":
            event.stop_event()
            yield await self._cmd_card(event, args)
            return

        creds = set_request_credentials(token or None, ticket or None)
        try:
            event.stop_event()
            ret = await self._call_with_auto_args(handler, event, args)
            if ret is not None:
                yield ret
        except Exception as e:
            logger.exception(f"指令执行失败: {cmd}, error={e}")
            yield event.plain_result(format_command_error(cmd, e, self.command_catalog))
        finally:
            reset_request_credentials(creds)

    def _forced_llm(self, event: AstrMessageEvent, text: str):
        """被 @ 后强制走 LLM 回话，并屏蔽默认链路避免重复回复。"""
        prompt = (text or "").strip() or "你好"
        try:
            event.is_at_or_wake_command = True
            event.is_wake = True
        except Exception:
            pass
        try:
            event.should_call_llm(True)
        except Exception:
            pass
        return event.request_llm(prompt=prompt)
