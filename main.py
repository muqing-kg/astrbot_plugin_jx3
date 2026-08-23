import inspect
from pathlib import Path
from typing import cast

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
from astrbot.api import AstrBotConfig

from .core.sqlite import AsyncSQLiteDB
from .core.jx3api_data import JX3APIService
from .core.aijx3_data import AIJX3Service
from .core.jx3box_data import JX3BOXService
from .core.async_task import AsyncTask
from .core.bilei_data import BiLeidata
from .core.message import MessageBuilder
from .core.fun_basic import load_as_base64
from .core.session_store import CREDENTIAL_MISSING, SessionStore
from .core.session_policy import (
    GROUP_SECRET_FORBIDDEN,
    NEED_TICKET,
    NEED_TOKEN,
    UNBOUND_SERVER,
    CLAIM_PHRASE,
    hint_bind_denied,
    hint_bind_ok,
    hint_claim_ok,
    hint_claim_phrase,
    hint_claim_taken,
    hint_group_secret,
    hint_need_claim,
    hint_need_ticket,
    hint_need_token,
    hint_push_need_bind,
    hint_push_ok,
    hint_secret_saved,
    hint_umo_invalid,
    hint_unbound,
    inject_server_args,
    parse_admin_command,
    strip_command_prefix,
)
from .core.credentials import reset_request_credentials, set_request_credentials
from .core.page_api import SessionPageAPI


@register("astrbot_plugin_jx3",
          "fxdyz",
          "聚合剑网三游戏数据，提供查询、图片渲染、本地避雷和后台推送。",
          "3.3.0",
          "https://github.com/qsc20001102/astrbot_plugin_jx3"
)
class Jx3ApiPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.conf = config
        self.prefix = self.conf.get("prefix", {}) or {}
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
            await self.init_bilei_data()
            await self.init_achievement_cache_data()
            await self.sessions.init()
            await self.plugin_sql_db.connect()
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
        if self.jx3at:
            await self.jx3at.destroy()
        if self.jx3api:
            await self.jx3api.close()
        if self.aijx3:
            await self.aijx3.close()
        if self.jx3box:
            await self.jx3box.close()
        if self.local_sql_db:
            await self.local_sql_db.close()
        if self.plugin_sql_db:
            await self.plugin_sql_db.close()
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

    def create_all(self):
        self.local_sql_db = AsyncSQLiteDB(str(self.local_data_path))
        self.plugin_sql_db = AsyncSQLiteDB(str(self.plugin_data_path))
        self.sessions = SessionStore(self.local_sql_db)
        self.bilei = BiLeidata(self.local_sql_db)
        self.jx3api = JX3APIService(self.conf, self.plugin_sql_db, self.local_sql_db)
        self.aijx3 = AIJX3Service(self.conf, self.plugin_sql_db, self.local_sql_db)
        self.jx3box = JX3BOXService(self.conf, self.plugin_sql_db, self.local_sql_db)
        self.jx3at = AsyncTask(
            cast(Context, self.context),
            self.conf,
            self.jx3api,
            self.jx3box,
            self.sessions,
        )
        self.jx3cmd = MessageBuilder("", self.jx3api, self.aijx3, self.jx3box, self.bilei, self.jx3at, self.icons)

    async def init_bilei_data(self):
        await self.local_sql_db.connect()
        await self.local_sql_db.execute("""
        CREATE TABLE IF NOT EXISTS bilei(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            text TEXT,
            time TEXT,
            user TEXT
        )
        """)

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
            "日常": self.jx3cmd.richang,
            "日常预测": self.jx3cmd.richangyuche,
            "穹野卫": self.jx3cmd.qiongyewei,
            "披风会": self.jx3cmd.pifenghui,
            "云从社": self.jx3cmd.yunchongshe,
            "楚天社": self.jx3cmd.chutianshe,
            "关隘": self.jx3cmd.guanaishouling,
            "赤兔": self.jx3cmd.benrichitu,
            "本周赤兔": self.jx3cmd.benzhouchitu,
            "阵营奉献": self.jx3cmd.zhenyingevent,
            "烟花": self.jx3cmd.yanhuachaxun,
            "刷马": self.jx3cmd.shuma,
            "马场": self.jx3cmd.machang,
            "战绩": self.jx3cmd.zhanji,
            "名剑排行": self.jx3cmd.mingjianpaihang,
            "名剑统计": self.jx3cmd.mingjiantongji,
            "名士五十强": self.jx3cmd.mingshiwushiqiang,
            "老江湖五十强": self.jx3cmd.laojianghuwushiqiang,
            "兵甲藏家五十强": self.jx3cmd.bingjiacangjiawushiqiang,
            "名师五十强": self.jx3cmd.mingshiwushiqiang_mentor,
            "阵营英雄五十强": self.jx3cmd.zhengyingyingxiongwushiqiang,
            "薪火相传五十强": self.jx3cmd.xinhuoxiangchuanwushiqiang,
            "庐园广记一百强": self.jx3cmd.luyuanguangjiyibaiqiang,
            "浩气神兵宝甲五十强": self.jx3cmd.haoqishenbingbaojiawushiqiang,
            "恶人神兵宝甲五十强": self.jx3cmd.erenshenbingbaojiawushiqiang,
            "浩气爱心帮会五十强": self.jx3cmd.haoqiaixinbanghuiwushiqiang,
            "恶人爱心帮会五十强": self.jx3cmd.erenaixinbanghuiwushiqiang,
            "赛季恶人五十强": self.jx3cmd.saijierenwushiqiang,
            "赛季浩气五十强": self.jx3cmd.saijihaoqiwushiqiang,
            "上周恶人五十强": self.jx3cmd.shangzhouerenwushiqiang,
            "上周浩气五十强": self.jx3cmd.shangzhouhaoqiwushiqiang,
            "本周恶人五十强": self.jx3cmd.benzhouerenwushiqiang,
            "本周浩气五十强": self.jx3cmd.benzhouhaoqiwushiqiang,
            "试炼排行": self.jx3cmd.shilianpaixing,
            "阵营拍卖": self.jx3cmd.zhengyingpaimai,
            "的卢": self.jx3cmd.dilujilu,
            "金价": self.jx3cmd.jinjia,
            "物价": self.jx3cmd.wujia,
            "成本": self.jx3cmd.chengbeng,
            "看号": self.jx3cmd.kanhao,
            "帮战": self.jx3cmd.bangzhanjilu,
            "沙盘": self.jx3cmd.shapan,
            "诛恶": self.jx3cmd.zhueevent,
            "名片": self.jx3cmd.jueshemingpian,
            "全名片": self.jx3cmd.shuoyoumingpian,
            "随机秀": self.jx3cmd.shuijimingpian,
            "奇遇": self.jx3cmd.juesheqiyu,
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
            "阵眼": self.jx3cmd.zhenyan,
            "配装": self.jx3cmd.peizhuang,
            "资历排行": self.jx3cmd.zilipaixing,
            "技能": self.jx3cmd.jineng,
            "奇穴": self.jx3cmd.qixue,
            "聊天": self.jx3cmd.liaotian,
            "统战": self.jx3cmd.tongzhanyy,
            "小药": self.jx3cmd.xiaoyao,
            "骗子": self.jx3cmd.pianzhi,
            "花价": self.jx3cmd.huajia,
            "装饰": self.jx3cmd.zhuangshi,
            "器物": self.jx3cmd.qiwu,
            "拜师": self.jx3cmd.baishi,
            "收徒": self.jx3cmd.shoutu,
            "维护": self.jx3cmd.weihu,
            "新闻": self.jx3cmd.xinwen,
            "招募": self.jx3cmd.tuanduizhaomu,
            "团长": self.jx3cmd.tuanzhang,
            "团牌": self.jx3cmd.tuanpai,
            "答案之书": self.jx3cmd.daanzhishu,
            "舔狗语录": self.jx3cmd.tiangou,
            "疯狂星期四": self.jx3cmd.fkxq4,
            "彩虹屁": self.jx3cmd.caihongpi,
            "毒鸡汤": self.jx3cmd.dujitang,
            "朋友圈": self.jx3cmd.pengyouquan,
            "喝什么": self.jx3cmd.heshengme,
            "吃什么": self.jx3cmd.chishengme,
            "骚话": self.jx3cmd.shaohua,
            "渣男语录": self.jx3cmd.zhananyulu,
            "贴吧物价": self.jx3cmd.tiebawujia,
            "818": self.jx3cmd.bagua,
            "科举": self.jx3cmd.keju,
            "区服": self.jx3cmd.zhuangtai,
            "开服": self.jx3cmd.kaifu,
            "技改": self.jx3cmd.jigai,
            "解密": self.jx3cmd.jiemi,
            "副本": self.jx3cmd.fubeng,
            "掉落": self.jx3cmd.diaoluo,
            "宏": self.jx3cmd.hong,
            "资历": self.jx3cmd.zili,
            "交易行": self.jx3cmd.jiaoyihang,
            "避雷添加": self.jx3cmd.bilei_add,
            "避雷查看": self.jx3cmd.bilei_all,
            "避雷查询": self.jx3cmd.bilei_select,
            "避雷修改": self.jx3cmd.bilei_update,
            "避雷删除": self.jx3cmd.bilei_delete,
        }

    def parse_message(self, text: str) -> list[str] | None:
        return strip_command_prefix(text, bool(self.prefix.get("enable")), self.prefix.get("text") or "")

    def _event_umo(self, event: AstrMessageEvent) -> str:
        try:
            return str(event.unified_msg_origin or "").strip()
        except Exception:
            return ""

    def _event_display_name(self, event: AstrMessageEvent) -> str:
        try:
            group_id = str(event.get_group_id() or "").strip()
            if group_id:
                return f"群 {group_id}"
            sender = str(event.get_sender_id() or "").strip()
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
            return bool(hasattr(event, "is_admin") and callable(event.is_admin) and event.is_admin())
        except Exception:
            return False

    async def _is_plugin_admin(self, event: AstrMessageEvent) -> bool:
        if self._is_astrbot_admin(event):
            return True
        return await self.sessions.is_claimed_admin(self._sender_id(event))

    def _global_token(self) -> str:
        return str(self.conf.get("jx3api_token", "") or "").strip()

    def _global_ticket(self) -> str:
        return str(self.conf.get("jx3api_ticket", "") or "").strip()

    async def _handle_admin_command(self, event: AstrMessageEvent, parts: list[str]):
        parsed = parse_admin_command(parts, is_private=self._is_private(event))
        if parsed.error == GROUP_SECRET_FORBIDDEN:
            return event.plain_result(hint_group_secret())
        if parsed.error == "missing_server":
            return event.plain_result("用法：/绑定 区服名\n例如：/绑定 梦江南")
        if parsed.error == "missing_push_type":
            return event.plain_result("用法：/打开 新闻 或 /关闭 新闻\n可选：开服、新闻、刷马、赤兔")
        if parsed.error == "missing_secret_args":
            return event.plain_result("用法：/Token <UMO> <Token> 或 /推栏 <UMO> <推栏标识>")
        if parsed.error:
            return None

        if parsed.action == "claim":
            if parsed.value != CLAIM_PHRASE:
                return event.plain_result(hint_claim_phrase())
            if not (self._is_astrbot_admin(event) or not ((await self.sessions.get_admin()) or {}).get("user_id")):
                # 已有认领人时，仅 AstrBot 管理员或本人可重复认领
                if not await self._is_plugin_admin(event):
                    admin = await self.sessions.get_admin()
                    return event.plain_result(hint_claim_taken((admin or {}).get("name") or ""))
            ok, name = await self.sessions.claim_admin(self._sender_id(event), event.get_sender_name() if hasattr(event, "get_sender_name") else "")
            if not ok:
                return event.plain_result(hint_claim_taken(name))
            return event.plain_result(hint_claim_ok(name))

        if parsed.action == "token_stats":
            if not await self._is_plugin_admin(event):
                return event.plain_result(hint_need_claim())
            umo = self._event_umo(event)
            row = await self.sessions.get(umo)
            session_token = ((row or {}).get("token") or "").strip()
            global_token = self._global_token()
            blocks = []
            if session_token:
                data = await self.jx3api.token_stats(session_token)
                title = "【该群 Token】" if not self._is_private(event) else "【该会话 Token】"
                body = data.get("data") if data.get("code") == 200 else (data.get("msg") or "查询失败")
                blocks.append(title + "\n" + body)
            if global_token and global_token != session_token:
                data = await self.jx3api.token_stats(global_token)
                body = data.get("data") if data.get("code") == 200 else (data.get("msg") or "查询失败")
                blocks.append("【全局 Token】\n" + body)
            if not blocks:
                return event.plain_result(hint_need_token())
            return event.plain_result("\n\n".join(blocks))

        if parsed.action == "bind":
            if not await self._is_plugin_admin(event):
                return event.plain_result(hint_need_claim())
            umo = self._event_umo(event)
            await self.sessions.bind_server(umo, parsed.value, self._event_display_name(event))
            return event.plain_result(hint_bind_ok(parsed.value))

        if parsed.action in {"open_push", "close_push"}:
            if not await self._is_plugin_admin(event):
                return event.plain_result(hint_need_claim())
            umo = self._event_umo(event)
            await self.sessions.ensure(umo, self._event_display_name(event))
            ok, msg = await self.sessions.set_push(umo, parsed.value, parsed.action == "open_push")
            if not ok:
                return event.plain_result(hint_push_need_bind())
            await self.jx3at.refresh_jobs()
            return event.plain_result(hint_push_ok(parsed.value, parsed.action == "open_push"))

        if parsed.action in {"set_token", "set_ticket"}:
            if not await self._is_plugin_admin(event):
                return event.plain_result(hint_need_claim())
            target = parsed.target.strip()
            row = await self.sessions.get(target)
            if not row:
                return event.plain_result(hint_umo_invalid())
            if parsed.action == "set_token":
                await self.sessions.set_token(target, parsed.value)
                return event.plain_result(hint_secret_saved("token", target))
            await self.sessions.set_ticket(target, parsed.value)
            return event.plain_result(hint_secret_saved("ticket", target))
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

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        if not self.command_map:
            return
        parts = self.parse_message(event.message_str)
        if not parts:
            return

        admin_ret = await self._handle_admin_command(event, parts)
        if admin_ret is not None:
            event.stop_event()
            yield admin_ret
            return

        cmd, *args = parts
        handler = self.command_map.get(cmd)
        if not handler:
            return

        umo = self._event_umo(event)
        row = await self.sessions.ensure(umo, self._event_display_name(event))
        bound = (row.get("server") or "").strip()
        injected = inject_server_args(cmd, args, bound)
        if injected == UNBOUND_SERVER:
            event.stop_event()
            yield event.plain_result(hint_unbound())
            return
        args = injected

        if cmd in NEED_TOKEN:
            token = self.sessions.resolve_token(row, self._global_token())
            if token == CREDENTIAL_MISSING:
                event.stop_event()
                yield event.plain_result(hint_need_token())
                return
        else:
            token = self.sessions.resolve_token(row, self._global_token())
            if token == CREDENTIAL_MISSING:
                token = ""

        if cmd in NEED_TICKET:
            ticket = self.sessions.resolve_ticket(row, self._global_ticket())
            if ticket == CREDENTIAL_MISSING:
                event.stop_event()
                yield event.plain_result(hint_need_ticket())
                return
        else:
            ticket = self.sessions.resolve_ticket(row, self._global_ticket())
            if ticket == CREDENTIAL_MISSING:
                ticket = ""

        creds = set_request_credentials(token or None, ticket or None)
        try:
            event.stop_event()
            ret = await self._call_with_auto_args(handler, event, args)
            if ret is not None:
                yield ret
        except Exception as e:
            logger.exception(f"指令执行失败: {cmd}, error={e}")
            yield event.plain_result("参数错误或执行失败")
        finally:
            reset_request_credentials(creds)
