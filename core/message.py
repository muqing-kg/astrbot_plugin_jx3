import json as _json
import time
from xml.sax.saxutils import escape as _xml_escape

from astrbot.core import html_renderer
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain
from astrbot.api.message_components import Share
from astrbot.core.utils.session_waiter import (
    SessionController,
    session_waiter,
)

from .jx3api_data import JX3APIService
from .aijx3_data import AIJX3Service
from .jx3box_data import JX3BOXService
from .unua_data import UnuaService
from .async_task import AsyncTask
from .yymj_data import YymjGuideService
from .decorations import build_decorated_payload, estimate_body_length, fetch_poem_line
from .credentials import CredentialRuntimeError
from .render_meta import build_page_meta, limit_image_rows

class MessageBuilder:
    """回复消息构建"""
    RANKING_IDS = (
        "名剑排行", "名剑统计", "跨服名剑榜", "武林争霸赛", "捕快荣誉榜",
        "江湖浪客榜", "决斗挑战榜", "资历排行", "名士排行", "江湖排行",
        "兵甲排行", "名师排行", "阵营排行", "薪火排行", "家园排行",
        "浩气神兵排行", "恶人神兵排行", "浩气爱心排行", "恶人爱心排行",
    )
    ZHANGONG_ALL = (
        "本周恶人战功榜", "上周恶人战功榜", "赛季恶人战功榜",
        "本周浩气战功榜", "上周浩气战功榜", "赛季浩气战功榜",
    )
    ZHANGONG_EWE = ("本周恶人战功榜", "上周恶人战功榜", "赛季恶人战功榜")
    ZHANGONG_HAO = ("本周浩气战功榜", "上周浩气战功榜", "赛季浩气战功榜")
    CARD_IDS = ("名片", "全部名片")

    ZILI_MENU_TEXT = (
        "请选择资历查询类型：\n"
        "0. 资历总览\n"
        "1. 杂闻总览\n"
        "2. 武学总览\n"
        "3. 修为总览\n"
        "4. 装备总览\n"
        "5. 技艺总览\n"
        "6. 阅读总览\n"
        "7. 任务总览\n"
        "8. 足迹总览\n"
        "9. 战斗总览\n"
        "10. 声望总览\n"
        "11. 秘境总览\n"
        "12. 帮会总览\n"
        "13. 阵营总览\n"
        "14. 节日总览\n"
        "15. 活动总览\n"
        "16. 风雨江湖路总览\n"
        "17. 家园总览\n"
        "18. 剑侠录总览"
    )

    def __init__(self, 
                 server: str, 
                 jx3api: JX3APIService, 
                 aijx3: AIJX3Service,
                 jx3box: JX3BOXService,  
                 unua: UnuaService,
                 jx3at: AsyncTask, 
                 yymj: YymjGuideService,
                 icons: dict[str, dict[str, str]]
            ):
        self.server = server
        self.jx3api = jx3api
        self.aijx3 = aijx3
        self.jx3box = jx3box
        self.unua = unua
        self.jx3at = jx3at
        self.yymj = yymj
        self.icons = icons


    async def html_render(
        self,
        tmpl: str,
        data: dict,
        return_url=True,
        options: dict | None = None,
    ) -> str:
        """渲染 HTML"""
        for attempt in range(2):
            try:
                return await html_renderer.render_custom_template(
                    tmpl,
                    data,
                    return_url=return_url,
                    options=options,
                )
            except Exception as e:
                logger.warning(f"HTML 渲染失败，准备重试: {e}")
                if attempt == 1:
                    raise
        raise RuntimeError("渲染失败")
    

    async def plain_msg(self, event: AstrMessageEvent, action):
        """最终将数据整理成文本发送"""
        data= await action()
        try:
            if data["code"] == 200:
                await event.send( event.plain_result(data["data"]))
            else:
                await event.send(event.plain_result(data["msg"])) 
        except CredentialRuntimeError:
            raise
        except Exception as e:
            logger.error(f"功能函数执行错误: {e}")
            await event.send(event.plain_result("处理失败，请稍后再试"))


    async def T2I_image_msg(self, event: AstrMessageEvent, action):
        """最终将数据渲染成图片发送"""
        data = await action()
        try:
            if data["code"] == 200:
                options = {
                    "quality": 100,
                    "device_scale_factor_level": "normal",
                    "full_page": True,
                    "omit_background": False,
                    "type": "jpeg"
                }
                body_length = estimate_body_length(data.get("temp") or "", data["data"], self.icons)
                poem_line = await fetch_poem_line()
                data["data"].update(build_decorated_payload(self.icons, body_length, poem_line))
                if not data["data"].get("page_quote"):
                    quote = await self.jx3api.shaohua()
                    if quote.get("code") == 200 and quote.get("data"):
                        data["data"]["page_quote"] = str(quote["data"]).strip()
                data["data"] = limit_image_rows(data["temp"], data["data"])
                if not data["data"].get("page_meta"):
                    data["data"]["page_meta"] = build_page_meta(data.get("temp") or "", data["data"])
                note = str(data["data"].get("note") or "").strip()
                page_note = str(data["data"].get("page_note") or "").strip()
                if note:
                    page_note = " · ".join(part for part in (page_note, note) if part)
                if page_note:
                    data["data"]["page_note"] = page_note
                url = await self.html_render(data["temp"], data["data"], options=options)
                await event.send(event.image_result(url)) 
            else:
                await event.send(event.plain_result(data["msg"])) 

        except Exception as e:
            logger.error(f"功能函数执行错误: {e}")
            await event.send(event.plain_result("渲染图片失败，请稍后再试"))


    async def image_msg(self, event: AstrMessageEvent, action):
        """最终将数据整理成图片发送"""
        data = await action()
        try:
            if data["code"] == 200:
                await event.send(event.image_result(data["data"])) 
            else:
                await event.send(event.plain_result(data["msg"])) 

        except CredentialRuntimeError:
            raise
        except Exception as e:
            logger.error(f"功能函数执行错误: {e}")
            await event.send(event.plain_result("渲染图片失败，请稍后再试"))

    async def raw_image_msg(self, event: AstrMessageEvent, action):
        """渲染不套公共装饰层的独立图片。"""
        data = await action()
        try:
            if data["code"] == 200:
                options = {
                    "quality": 100,
                    "device_scale_factor_level": "normal",
                    "full_page": True,
                    "omit_background": False,
                    "type": "png"
                }
                url = await self.html_render(data["temp"], data["data"], options=options)
                await event.send(event.image_result(url))
            else:
                await event.send(event.plain_result(data["msg"]))
        except CredentialRuntimeError:
            raise
        except Exception as e:
            logger.error(f"功能函数执行错误: {e}")
            await event.send(event.plain_result("渲染图片失败，请稍后再试"))


    async def plain_chain(self, event: AstrMessageEvent, action):
        """富媒体消息"""
        data= await action()
        try:
            if data["code"] == 200:
                await event.send(event.chain_result(data["data"]))
            else:
                await event.send(event.plain_result(data["msg"])) 
        except CredentialRuntimeError:
            raise
        except Exception as e:
            logger.error(f"功能函数执行错误: {e}")
            await event.send(event.plain_result("渲染图片失败，请稍后再试"))

    async def link_card_msg(self, event: AstrMessageEvent, action):
        """标题/链接/封面打包成平台卡片发送。"""
        data = await action()
        try:
            if data["code"] == 200:
                payload = data["data"]
                if self._is_wechat_session(event):
                    await self._send_wechat_appmsg(event, payload)
                elif self._is_qq_session(event):
                    await self._send_qq_json_card(event, payload)
                else:
                    segment = Share(
                        url=payload["url"],
                        title=payload["title"],
                        content=payload.get("desc") or "",
                        image=payload.get("image") or "",
                    )
                    await event.send(event.chain_result([segment]))
            else:
                await event.send(event.plain_result(data["msg"]))
        except CredentialRuntimeError:
            raise
        except Exception as e:
            logger.error(f"发送链接卡片失败: {e}")
            fallback = data.get("data") or {}
            if fallback.get("title") and fallback.get("url"):
                await event.send(event.plain_result(f'{fallback["title"]}\n{fallback["url"]}'))
            else:
                await event.send(event.plain_result("发送卡片失败，请稍后再试"))

    @staticmethod
    def _is_wechat_session(event: AstrMessageEvent) -> bool:
        """AstrBot 平台 ID 由用户配置；WeChatBridge 常见为“微信-*”。"""
        group_id = str(event.get_group_id() or "").strip()
        marker = " ".join(
            (
                str(event.get_platform_id() or ""),
                str(event.get_platform_name() or ""),
            )
        ).lower()
        return (
            group_id.endswith("@chatroom")
            or "微信" in marker
            or "wechat" in marker
            or "weixin" in marker
        )

    @staticmethod
    def _is_qq_session(event: AstrMessageEvent) -> bool:
        marker = " ".join(
            (
                str(event.get_platform_id() or ""),
                str(event.get_platform_name() or ""),
            )
        ).lower()
        return "qq" in marker or str(event.get_platform_name() or "") == "aiocqhttp"

    async def _send_onebot_segments(self, event: AstrMessageEvent, segments: list[dict]):
        bot = getattr(event, "bot", None)
        if bot is None:
            raise RuntimeError("当前平台不支持原生卡片")
        group_id = str(event.get_group_id() or "").strip()
        caller = getattr(bot, "call_action", None)
        if group_id:
            if caller:
                await caller("send_group_msg", group_id=group_id, message=segments)
            else:
                await bot.send_group_msg(group_id=group_id, message=segments)
        else:
            user_id = str(event.get_sender_id() or event.get_session_id() or "").strip()
            if caller:
                await caller("send_private_msg", user_id=user_id, message=segments)
            else:
                await bot.send_private_msg(user_id=user_id, message=segments)

    async def _send_wechat_appmsg(self, event: AstrMessageEvent, payload: dict):
        title = _xml_escape(str(payload.get("title") or "攻略"))
        desc = _xml_escape(str(payload.get("desc") or ""))
        url = _xml_escape(str(payload.get("url") or ""))
        cover = _xml_escape(str(payload.get("image") or ""))
        appmsg = (
            '<appmsg appid="" sdkver="0">'
            f"<title>{title}</title>"
            f"<des>{desc}</des>"
            "<action>view</action>"
            "<type>5</type>"
            f"<url>{url}</url>"
            f"<thumburl>{cover}</thumburl>"
            "<appinfo><version>1</version><appname>链接</appname></appinfo>"
            "</appmsg>"
        )
        segment = {
            "type": "wechat_appmsg",
            "data": {
                "content": appmsg,
                "type": "5",
            },
        }
        await self._send_onebot_segments(event, [segment])

    async def _send_qq_json_card(self, event: AstrMessageEvent, payload: dict):
        title = str(payload.get("title") or "攻略").strip()
        desc = str(payload.get("desc") or "").strip()
        url = str(payload.get("url") or "").strip()
        cover = str(payload.get("image") or "").strip()
        now = int(time.time())
        card = {
            "app": "com.tencent.structmsg",
            "desc": "攻略",
            "view": "news",
            "ver": "0.0.0.1",
            "prompt": title,
            "config": {
                "forward": True,
                "type": "news",
                "autosize": True,
            },
            "extra": {"app_type": 1, "appid": 0, "msg_seq": 0, "uin": 0},
            "meta": {
                "news": {
                    "action": "",
                    "android_pkg_name": "",
                    "app_type": 1,
                    "appid": 100951776,
                    "ctime": now,
                    "desc": desc,
                    "jumpUrl": url,
                    "preview": cover,
                    "source_icon": "",
                    "source_url": "",
                    "tag": str(payload.get("author") or "隐元秘鉴"),
                    "time": now,
                    "title": title,
                }
            },
        }
        segment = {
            "type": "json",
            "data": {
                "data": _json.dumps(
                    card,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            },
        }
        await self._send_onebot_segments(event, [segment])


    @property
    def command_catalog(self):
        return getattr(self.jx3api, "command_catalog", None) or None

    def _cmd_display_name(self, command_id: str) -> str:
        if not self.command_catalog:
            return command_id
        return str((self.command_catalog.get(command_id) or {}).get("command") or command_id)

    async def _send_choice_and_wait(
        self,
        event: AstrMessageEvent,
        menu_text: str,
        count: int,
        runner,
        *,
        allow_zero: bool = False,
        timeout: int = 10,
    ):
        text = str(menu_text).rstrip()
        resolved = False
        if "发送序号即可" not in text:
            text += f"\n\n发送序号即可，{timeout} 秒后自动选 1"
        await event.send(event.plain_result(text))
        user_id = event.get_sender_id()

        @session_waiter(timeout=timeout)
        async def choice_waiter(controller: SessionController, new_event: AstrMessageEvent):
            nonlocal resolved
            if new_event.get_sender_id() != user_id:
                return
            msg = new_event.get_message_str().strip()
            if msg.startswith("/"):
                msg = msg[1:].strip()
            if not msg.isdigit():
                await new_event.send(MessageChain().message("输入异常，结束会话"))
                controller.stop()
                return
            choice = int(msg)
            if allow_zero:
                if choice < 0 or choice > count:
                    await new_event.send(MessageChain().message("无效序号，结束会话"))
                    controller.stop()
                    return
            elif choice < 1 or choice > count:
                await new_event.send(MessageChain().message("无效序号，结束会话"))
                controller.stop()
                return
            resolved = True
            try:
                await runner(choice, new_event)
            except Exception as e:
                logger.error(f"执行命令错误: {e}")
                await new_event.send(MessageChain().message("处理失败，请稍后再试"))
            controller.stop()

        try:
            await choice_waiter(event)
        except TimeoutError:
            if resolved:
                return
            try:
                await runner(1, event)
            except Exception as e:
                logger.error(f"默认选项执行错误: {e}")
                await event.send(event.plain_result("处理失败，请稍后再试"))
        except Exception:
            logger.error("选择等待异常", exc_info=True)

    async def _send_command_menu(
        self,
        event: AstrMessageEvent,
        title: str,
        ids: tuple[str, ...],
        runner,
        timeout: int = 10,
    ):
        lines = "\n".join(f"{index}. {self._cmd_display_name(item)}" for index, item in enumerate(ids, 1))
        await self._send_choice_and_wait(event, f"{title}\n{lines}", len(ids), runner, timeout=timeout)

    async def send_command_menu(
        self,
        event: AstrMessageEvent,
        title: str,
        ids: tuple[str, ...],
        runner,
        timeout: int = 10,
    ):
        await self._send_command_menu(event, title, ids, runner, timeout=timeout)

    async def handler_plain_image_msg(self, event: AstrMessageEvent, action1, action2):
        """两轮会话：先发文字序号列表，选择后返回正文与图片"""
        data = await action1()
        if data.get("code") != 200:
            await event.send(event.plain_result(data.get("msg") or "未搜索到相关内容"))
            return

        items = data["data"]["list"]
        count = max(0, len(items) - 1)
        if count <= 0:
            await event.send(event.plain_result("未搜索到相关内容"))
            return

        async def runner(num: int, reply_event: AstrMessageEvent):
            detail = await action2(items[num])
            if detail.get("code") != 200:
                await reply_event.send(MessageChain().message(detail.get("msg") or "获取详细数据失败"))
                return
            chain = MessageChain()
            chain.message(detail.get("data") or "")
            if detail.get("temp"):
                from html import escape
                text = escape(str(detail.get("temp") or ""), quote=True)
                text = text.replace("{", "&#123;").replace("}", "&#125;").replace("\n", "<br>")
                url = await self.html_render(
                    f"<div style='font-family: sans-serif; padding: 12px;'>{text}</div>",
                    {},
                    options={},
                )
                chain.url_image(url)
            await reply_event.send(chain)

        await self._send_choice_and_wait(
            event,
            data.get("msg") or "请选择序号",
            count,
            runner,
        )


    async def handler_zili_msg(self, event: AstrMessageEvent, name: str, server: str):
        """资历查询两轮会话：先出文字菜单，选择后渲染对应分布图"""
        async def runner(choice: int, reply_event: AstrMessageEvent):
            data = await self.jx3box.zili(name, server, choice)
            if data.get("code") != 200:
                await reply_event.send(MessageChain().message(data.get("msg", "获取资历数据失败")))
                return

            options = {
                "quality": 100,
                "device_scale_factor_level": "normal",
                "full_page": True,
                "omit_background": False,
                "type": "jpeg"
            }
            body_length = estimate_body_length(data.get("temp") or "", data["data"], self.icons)
            poem_line = await fetch_poem_line()
            data["data"].update(build_decorated_payload(self.icons, body_length, poem_line))
            data["data"]["page_meta"] = " · ".join(part for part in (
                str(data["data"].get("server") or "").strip(),
                str(data["data"].get("role_name") or "").strip(),
                str(data["data"].get("title") or "").strip(),
                str(data["data"].get("update_time") or "").strip(),
            ) if str(part or "").strip())
            url = await self.html_render(data["temp"], data["data"], options=options)
            await reply_event.send(reply_event.image_result(url))

        await self._send_choice_and_wait(
            event,
            self.ZILI_MENU_TEXT,
            18,
            runner,
            allow_zero=True,
        )


    async def  helps(self, event: AstrMessageEvent, display_name: str = "", server: str = ""):
        """ 功能"""
        return await self.T2I_image_msg(
            event,
            lambda: self.jx3api.helps(display_name, server),
        )

    async def  notice_manage(self, event: AstrMessageEvent, display_name: str = "", server: str = "", enabled=None):
        """ 通知管理 """
        return await self.T2I_image_msg(
            event,
            lambda: self.jx3api.notice_manage(display_name, server, enabled or set()),
        )


    async def  richang(self, event: AstrMessageEvent, num: int = 0):
        """ 日常 天数"""
        return await self.plain_msg(event, lambda: self.jx3api.richang("day",num))


    async def  richangyuche(self, event: AstrMessageEvent):
        """ 日常预测"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.richang("list",15))


    async def  qiongyewei(self, event: AstrMessageEvent):
        """ 穹野卫"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.xingxiashijian("穹野卫"))
    
    async def  pifenghui(self, event: AstrMessageEvent):
        """ 披风会"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.xingxiashijian("披风会"))

    async def  yunchongshe(self, event: AstrMessageEvent):
        """ 云从社"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.xingxiashijian("云从社"))

    async def  chutianshe(self, event: AstrMessageEvent):
        """ 楚天社 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.xingxiashijian("楚天社"))

    async def  benrichitu(self, event: AstrMessageEvent):
        """ 本日赤兔"""
        return await self.plain_msg(event, self.jx3api.benrichitu)

    async def  benzhouchitu(self, event: AstrMessageEvent):
        """ 本周赤兔"""
        return await self.plain_msg(event, self.jx3api.benzhouchitu)

    async def  yanhuachaxun(self, event: AstrMessageEvent,server: str = "",name: str = "" ):
        """ 烟花 服务器 角色"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.yanhuachaxun(server,name))

    async def  shuma(self, event: AstrMessageEvent,server: str ): 
        """ 刷马 服务器"""
        return await self.plain_msg(event, lambda: self.jx3api.shuma(server))

    async def  machang(self, event: AstrMessageEvent,server: str ): 
        """ 马场 服务器"""
        return await self.plain_msg(event, lambda: self.jx3api.machang(server,1))

    async def  zhanji(self, event: AstrMessageEvent, server: str ,name: str , mode:str = "33"):
        """ 战绩 服务器 角色 模式"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.zhanji(name, server,mode))

    async def  mingjianpaihang(self, event: AstrMessageEvent, mode:str = "33",limit: int = 50):
        """ 名剑排行 模式 数量 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.mingjianpaihang(limit,mode))

    async def  mingjiantongji(self, event: AstrMessageEvent,mode: str = "33"):
        """ 名剑统计 模式"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.mingjiantongji(mode))

    async def  mingshiwushiqiang(self, event: AstrMessageEvent, server: str):
        """ 名士五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("名士五十强", server))

    async def  laojianghuwushiqiang(self, event: AstrMessageEvent, server: str):
        """ 老江湖五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("老江湖五十强", server))

    async def  bingjiacangjiawushiqiang(self, event: AstrMessageEvent, server: str):
        """ 兵甲藏家五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("兵甲藏家五十强", server))

    async def  mingshiwushiqiang_mentor(self, event: AstrMessageEvent, server: str):
        """ 名师五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("名师五十强", server))

    async def  zhengyingyingxiongwushiqiang(self, event: AstrMessageEvent, server: str):
        """ 阵营英雄五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("阵营英雄五十强", server))

    async def  xinhuoxiangchuanwushiqiang(self, event: AstrMessageEvent, server: str):
        """ 薪火相传五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("薪火相传五十强", server))

    async def  luyuanguangjiyibaiqiang(self, event: AstrMessageEvent, server: str):
        """ 庐园广记一百强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("庐园广记一百强", server))

    async def  haoqishenbingbaojiawushiqiang(self, event: AstrMessageEvent, server: str):
        """ 浩气神兵宝甲五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("浩气神兵宝甲五十强", server))

    async def  erenshenbingbaojiawushiqiang(self, event: AstrMessageEvent, server: str ):
        """ 恶人神兵宝甲五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("恶人神兵宝甲五十强", server))

    async def  haoqiaixinbanghuiwushiqiang(self, event: AstrMessageEvent, server: str ):
        """ 浩气爱心帮会五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("浩气爱心帮会五十强", server))

    async def  erenaixinbanghuiwushiqiang(self, event: AstrMessageEvent, server: str ):
        """ 恶人爱心帮会五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("恶人爱心帮会五十强", server))

    async def  saijierenwushiqiang(self, event: AstrMessageEvent, server: str):
        """ 赛季恶人五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("赛季恶人五十强", server))

    async def  saijihaoqiwushiqiang(self, event: AstrMessageEvent, server: str ):
        """ 赛季浩气五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("赛季浩气五十强", server))

    async def  shangzhouerenwushiqiang(self, event: AstrMessageEvent, server: str ):
        """ 上周恶人五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("上周恶人五十强", server))

    async def  shangzhouhaoqiwushiqiang(self, event: AstrMessageEvent, server: str ):
        """ 上周浩气五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("上周浩气五十强", server))

    async def  benzhouerenwushiqiang(self, event: AstrMessageEvent, server: str ):
        """ 本周恶人五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("本周恶人五十强", server))

    async def  benzhouhaoqiwushiqiang(self, event: AstrMessageEvent, server: str ):
        """ 本周浩气五十强 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.rank_statistical("本周浩气五十强", server))

    async def  shilianpaixing(self, event: AstrMessageEvent, server: str , name: str):
        """ 试炼排行 服务器 心法 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.shilianpaixing(name, server))

    async def  kuafumingjian(self, event: AstrMessageEvent, server: str = "", mode: str = "33"):
        """ 跨服名剑 [服务器] [模式] """
        return await self.T2I_image_msg(event, lambda: self.jx3api.kuafumingjian(server, mode))

    async def  wulinzhengba(self, event: AstrMessageEvent, camp: str = "恶人"):
        """ 武林争霸赛 [阵营] """
        return await self.T2I_image_msg(event, lambda: self.jx3api.wulinzhengba(camp))

    async def  bukuai(self, event: AstrMessageEvent, server: str = ""):
        """ 捕快 [服务器] """
        return await self.T2I_image_msg(event, lambda: self.jx3api.bukuai(server))

    async def  langke(self, event: AstrMessageEvent, server: str = ""):
        """ 浪客 [服务器] """
        return await self.T2I_image_msg(event, lambda: self.jx3api.langke(server))

    async def  juedou(self, event: AstrMessageEvent, server: str = "", mode: str = "公开"):
        """ 决斗 [服务器] [公开/私密] """
        return await self.T2I_image_msg(event, lambda: self.jx3api.juedou(server, mode))

    async def  zilifenbu(self, event: AstrMessageEvent, server: str, name: str, class_id: str = "1", subclass: str = ""):
        """ 资历分布 服务器 角色 [分类] """
        return await self.T2I_image_msg(event, lambda: self.jx3api.zilifenbu(server, name, class_id, subclass))

    async def  waiguansousuo(self, event: AstrMessageEvent, name: str):
        """ 外观搜索 关键词 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.waiguansousuo(name))

    async def  zhengyingpaimai(self, event: AstrMessageEvent,server: str , name: str = "", limit: int = 50 ):
        """ 阵营拍卖 [服务器] [物品] [数量] """
        return await self.T2I_image_msg(event, lambda: self.jx3api.zhengyingpaimai(server, name, limit))

    async def  dilujilu(self, event: AstrMessageEvent,server: str ):
        """ 的卢拍卖 [服务器] """
        return await self.T2I_image_msg(event, lambda: self.jx3api.dilujilu(server))

    async def  jinjia(self, event: AstrMessageEvent,server: str , limit:str = "15"):
        """ 金价 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.jinjia( server,limit))

    async def  wujia(self, event: AstrMessageEvent,Name: str , server: str = ""):
        """ 物价 外观名称 服务器"""    
        return await self.T2I_image_msg(event, lambda: self.jx3api.wujia(Name, server))

    async def  chengbeng(self, event: AstrMessageEvent, server: str ,Name: str ,source : int = 0):
        """ 成本 服务器 物品名称 """    
        return await self.T2I_image_msg(event, lambda: self.jx3api.chengbeng(Name, server,source)) 

    async def  kanhao(self, event: AstrMessageEvent,id: str):
        """ 看号 万宝楼编号 """    
        return await self.plain_msg(event, lambda: self.jx3api.bianhao(id)) 

    async def  bangzhanjilu(self, event: AstrMessageEvent, server: str):
        """ 帮战 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.bangzhanjilu(server))

    async def  shapan(self, event: AstrMessageEvent,server: str = ""):
        """ 沙盘 服务器"""
        return await self.raw_image_msg(event, lambda: self.jx3api.shapan(server))

    async def  zhueevent(self, event: AstrMessageEvent, server: str):
        """ 诛恶事件 服务器"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.zhueevent(server,20))

    async def  jueshemingpian(self, event: AstrMessageEvent, server: str , name: str , ):
        """ 名片 服务器 角色 """
        return await self.plain_chain(event, lambda: self.jx3api.jueshemingpian(server, name)) 

    async def  shuoyoumingpian(self, event: AstrMessageEvent, server: str, name: str, ):
        """ 全名片 服务器 角色 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.shuoyoumingpian(server,name))

    async def  shuijimingpian(self, event: AstrMessageEvent,server: str, force: str = "", body: str = "", ):
        """ 随机秀 服务器 门派 体型 """
        return await self.plain_chain(event, lambda: self.jx3api.shuijimingpian(server,force,body))

    async def  qiyuhuizong(self, event: AstrMessageEvent,server: str, num: str = "7" ):
        """ 汇总 服务器 天数 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.qiyuhuizong(server, num))

    async def  weizuoqiyu(self, event: AstrMessageEvent,server: str, name: str, ):
        """ 未出 服务器 角色 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.weizuoqiyu(server,name))

    async def  jinqiqiyu(self, event: AstrMessageEvent,server: str, limit: int = 20):
        """ 近期 服务器 数量"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.jinqiqiyu(server,limit))

    async def  juesheqiyu(self, event: AstrMessageEvent, server: str, name: str):
        """ 查询 服务器 角色 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.juesheqiyu(server,name, 0))

    async def  qiyutongji(self, event: AstrMessageEvent,adventureName: str, server: str = "",limit: int = 20):
        """ 统计 奇遇 服务器 数量"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.qiyutongji(adventureName,server,limit))

    async def  qiyugonglue(self, event: AstrMessageEvent,name: str):
        """ 攻略 奇遇"""
        return await self.link_card_msg(event, lambda: self.yymj.qiyugonglue(name))

    async def  jingnai(self, event: AstrMessageEvent, server: str, name: str):
        """ 精耐 服务器 角色 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.jingnai(name, server))
    
    async def  baizhan(self, event: AstrMessageEvent):
        """ 百战"""
        return await self.T2I_image_msg(event, self.jx3api.baizhan)
    
    async def  chengjiu(self, event: AstrMessageEvent, server:str, role:str, name:str):
        """ 成就 服务器 角色 成就"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.chengjiuchaxun(server,role,name))

    async def  jueshe(self, event: AstrMessageEvent,server: str, name: str):
        """ 角色 服务器 名称 """
        return await self.plain_msg(event, lambda: self.jx3api.jueshe(server, name, 1))

    async def  unua_online(self, event: AstrMessageEvent, server: str, name: str):
        """ 在线 服务器 角色名 """
        tong_name = ""
        try:
            detail = await self.jx3api._base_request(
                "/role/detail", {"server": server, "name": name, "history": 0, "token": self.jx3api.token}
            )
            if isinstance(detail, dict):
                tong_name = str(detail.get("tongName") or "").strip()
        except Exception:
            pass
        return await self.plain_msg(event, lambda: self.unua.role_online(server, name, tong_name))

    async def  zhenyan(self, event: AstrMessageEvent, name: str):
        """ 阵眼 心法"""
        return await self.plain_msg(event, lambda: self.jx3api.zhenyan(name))

    async def  peizhuang(self, event: AstrMessageEvent,name: str, tags: str = ""):
        """ 配装 心法 类型"""
        return await self.plain_msg(event, lambda: self.jx3box.peizhuang(name,tags))

    async def  zilipaixing(self, event: AstrMessageEvent, server: str = "", school: str = ""):
        """ 资历排行 服务器 门派 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.zilipaixing(server, school))

    async def  jineng(self, event: AstrMessageEvent, name: str):
        """ 技能 心法"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.jineng(name,0))

    async def  qixue(self, event: AstrMessageEvent, name: str):
        """ 奇穴 心法"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.qixue(name,0))

    async def  liaotian(self, event: AstrMessageEvent, server:str, name: str, limit:int = 20, page:int = 1):
        """ 聊天 服务器 角色 条数 页数"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.juesheliaotian(server,name,limit,page))

    async def  tongzhanyy(self, event: AstrMessageEvent, server: str = ""):
        """ 统战 服务器"""
        return await self.plain_msg(event, lambda: self.jx3api.tongzhanyy(server))

    async def  xiaoyao(self, event: AstrMessageEvent, name:str = ""):
        """ 小药 心法"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.xiaoyao(name))


    async def  huajia(self, event: AstrMessageEvent,  server: str, name: str= "" , map: str= ""):
        """ 花价 服务器 名称 地图"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.huajia(server,name,map))

    async def  zhuangshi(self, event: AstrMessageEvent,  name: str):
        """ 装饰 名称"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.zhuangshi(name))

    async def  qiwu(self, event: AstrMessageEvent,  name: str):
        """ 器物 地图名称"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.qiwu(name))

    async def  baishi(self, event: AstrMessageEvent, server: str, keyword: str = ""):
        """ 拜师 服务器 关键词 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.shitu(2, server, keyword, 50))

    async def  shoutu(self, event: AstrMessageEvent, server: str, keyword: str = ""):
        """ 收徒 服务器 关键词 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.shitu(1, server, keyword, 50))

    async def  weihu(self, event: AstrMessageEvent,limit:int = 5):
        """ 维护 数量"""
        return await self.plain_msg(event, lambda: self.jx3api.weihu(limit))

    async def  xinwen(self, event: AstrMessageEvent,limit:int = 5):
        """ 新闻 数量"""
        return await self.plain_msg(event, lambda: self.jx3api.xinwen(limit))

    async def  tuanduizhaomu(self, event: AstrMessageEvent,server: str, keyword: str = ""):
        """ 招募 服务器 副本"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.tuanduizhaomu( server,1,keyword,50))

    async def  tuanzhang(self, event: AstrMessageEvent,server: str, keyword: str = ""):
        """ 团长 服务器 名字"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.tuanduizhaomu( server,2,keyword,50))

    async def  tuanpai(self, event: AstrMessageEvent,server: str, keyword: str = ""):
        """ 团牌 服务器 内容"""
        return await self.T2I_image_msg(event, lambda: self.jx3api.tuanduizhaomu( server,3,keyword,50))

    async def  daanzhishu(self, event: AstrMessageEvent):
        """ 答案之书"""
        return await self.plain_msg(event, self.jx3api.daanzhishu)

    async def  tiangou(self, event: AstrMessageEvent):
        """ 舔狗语录"""
        return await self.plain_msg(event, self.jx3api.tiangou)

    async def  heshengme(self, event: AstrMessageEvent,):
        """ 喝什么"""
        return await self.plain_msg(event, self.jx3api.heshengme)

    async def  chishengme(self, event: AstrMessageEvent,):
        """ 吃什么"""
        return await self.plain_msg(event, self.jx3api.chishengme)

    async def  shaohua(self, event: AstrMessageEvent,):
        """ 骚话"""
        return await self.plain_msg(event, self.jx3api.shaohua)

    async def  zhananyulu(self, event: AstrMessageEvent,):
        """ 渣男语录"""
        return await self.plain_msg(event, self.jx3api.zhananyulu)

    async def  keju(self, event: AstrMessageEvent,subject: str, limit: int = 5):
        """ 科举 题目 条数"""
        return await self.plain_msg(event, lambda: self.jx3api.keju(subject,limit))

    async def  kaifu(self, event: AstrMessageEvent,server: str):
        """ 开服 服务器"""
        return await self.plain_msg(event, lambda: self.jx3api.kaifu(server))

    async def  jigai(self, event: AstrMessageEvent,):
        """ 技改"""
        return await self.plain_msg(event, self.jx3api.jigai)

    async def  diaoluo(self, event: AstrMessageEvent, name: str,  server: str = "", limit: str = "20",):
        """ 掉落 物品 服务器 数量 """
        return await self.T2I_image_msg(event, lambda: self.jx3api.diaoluo(name, server, limit))


    async def  hong(self, event: AstrMessageEvent,name: str):
        """ 宏 心法"""
        return await self.handler_plain_image_msg(event, lambda: self.jx3box.hong1(name), self.jx3box.hong2)

    async def  zili(self, event: AstrMessageEvent, server: str, name: str):
        """ 资历 角色名称 服务器"""
        return await self.handler_zili_msg(event, name, server)

    async def  jiaoyihang(self, event: AstrMessageEvent,server: str, Name: str):
        """ 交易行 物品名称 服务器"""     
        return await self.T2I_image_msg(event, lambda: self.jx3box.jiaoyihang(Name,server))


