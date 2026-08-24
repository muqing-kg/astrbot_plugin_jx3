import json
import html
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from inspect import isawaitable
from typing import Any, Awaitable, Callable, Dict, Optional

from astrbot.api import logger
from astrbot.api import AstrBotConfig
import astrbot.api.message_components as Comp

from .request import APIClient
from .sqlite import AsyncSQLiteDB
from .fun_basic import load_template,gold_to_parts,week_to_num,compare_date_str,format_time,format_remaining
from .credentials import current_token, current_ticket





class JX3APIService:
    def __init__(self, config: AstrBotConfig, sqlite: AsyncSQLiteDB, cache_sqlite: Optional[AsyncSQLiteDB] = None):
        # 实例化 API Client
        self._api: APIClient = APIClient()
        # 引用插件配置文件
        self._config = config
        # 引用sqlite
        self._sql_db = sqlite
        self._cache_db = cache_sqlite or sqlite

        # 获取配置中的 Token
        self._global_token = self._config.get("jx3api_token", "") or ""
        self._global_ticket = self._config.get("jx3api_ticket", "") or ""
        if not self._global_token:
            logger.warning("未配置全局 JX3API Token，未勾选使用全局的会话将无法使用付费功能")
        if not self._global_ticket:
            logger.warning("未配置全局推栏标识，需要推栏的功能将依赖全局或会话自定义配置")
        

    @property
    def token(self) -> str:
        return current_token(self._global_token)

    @property
    def ticket(self) -> str:
        return current_ticket(self._global_ticket)

    async def close(self):
        """释放底层 APIClient 资源"""
        if self._api:
            await self._api.close()


    def _init_return_data(self) -> Dict[str, Any]:
            """初始化标准的返回数据结构"""
            return {
                "code": 0,
                "msg": "功能函数未执行",
                "data": {},
                "temp": "",
                "icons": {}
            }

    
    async def _base_request(
        self, 
        api_path: str, 
        params: Optional[Dict[str, Any]] = None, 
        out: Optional[str] = "data"
    ) -> Optional[Any]:
        """
        基础请求封装，处理配置获取和API调用。
        """
        try:
            if not self._api:
                logger.error("API client is not initialized")
                return None

            base_url = "https://www.jx3api.com"
            api_url = base_url + api_path
            data = await self._api.get(api_url, params=params, out_key=out)
            
            if not data:
                logger.warning(f"获取接口信息失败或返回空数据: {api_url}")
            
            return data
            
        except Exception as e:
            logger.error(f"基础请求调用出错 ({api_path}): {e}")
            return None


    async def _request_api(
        self,
        path: str,
        params: Dict[str, Any],
        processor: Optional[
            Callable[[Any, Dict[str, Any]], Any | Awaitable[Any]]
        ] = None,
        template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """通用接口请求与模板处理。"""
        return_data = self._init_return_data()

        data = await self._base_request(path, params)
        if isinstance(data, dict) and data.get("_error"):
            return_data["msg"] = self._token_error_message(data.get("_error"))
            return return_data
        if data is None:
            return_data["msg"] = "获取接口信息失败"
            return return_data

        try:
            await processor(data, return_data)
        except Exception as e:
            logger.exception(f"数据处理时出错: {e}")
            return_data["msg"] = "处理接口返回信息时出错"
            return return_data

        if return_data.get("msg") and return_data.get("msg") != "功能函数未执行":
            return return_data

        # template 为空时不加载模板
        if template:
            try:
                return_data["temp"] = await load_template(template)
            except FileNotFoundError as e:
                logger.error(f"加载模板失败: {e}")
                return_data["msg"] = "系统错误：模板文件不存在"
                return return_data

        return_data["code"] = 200
        return return_data

    def _as_list(self, data: Any) -> list:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "list", "items", "records"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _pick(self, item: Any, *keys, default: str = "") -> str:
        if not isinstance(item, dict):
            return default if default else str(item or "")
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return str(value)
        return default

    def _now_text(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _token_error_message(self, raw: Any) -> str:
        text = str(raw or "").strip()
        lowered = text.lower()
        if any(key in lowered for key in ("expire", "expired")) or "过期" in text:
            return "JX3API Token 已过期，请更换或续费后再试。可发送 /查询令牌 查看状态。"
        if any(key in lowered for key in ("quota", "limit", "remaining", "insufficient", "count")) or any(key in text for key in ("次数", "余额", "额度", "用尽", "不足")):
            return "JX3API Token 次数已用尽，请更换或续费后再试。可发送 /查询令牌 查看剩余次数。"
        if "token" in lowered or "令牌" in text:
            return f"JX3API Token 不可用：{text}。可发送 /查询令牌 查看状态。"
        return text or "获取接口信息失败"

    def _table_data(self, title: str, columns: list[str], rows: list[list[str]], subtitle: str = "", note: str = "") -> dict:
        return {
            "title": title,
            "subtitle": subtitle or f"更新时间：{self._now_text()}",
            "note": note,
            "columns": columns,
            "rows": rows,
        }

    def _set_table(self, return_data: Dict[str, Any], title: str, columns: list[str], rows: list[list[str]], subtitle: str = "", empty_msg: str = "暂无数据") -> None:
        if not rows:
            return_data["msg"] = empty_msg
            return
        return_data["data"] = self._table_data(title, columns, rows, subtitle)

    def _arena_mode_code(self, mode: str) -> int:
        text = str(mode or "").strip().lower()
        if text in {"", "1", "33", "3v3", "3"}:
            return 1
        if text in {"0", "2", "22", "2v2"}:
            return 0
        if text in {"55", "5v5", "5"}:
            return 2
        return 1

    def _camp_code(self, camp: str) -> int:
        text = str(camp or "").strip()
        if text in {"2", "恶人", "恶人谷"}:
            return 2
        return 1

    def _wanted_mode(self, mode: str) -> int:
        text = str(mode or "").strip()
        if text in {"2", "私密"}:
            return 2
        return 1

    # --- 业务功能函数 ---
    async def helps(self) -> Dict[str, Any]:
        """帮助"""
        return_data = self._init_return_data()
        
        # 加载模板
        try:
            return_data["temp"] = await load_template("helps.html")
        except FileNotFoundError as e:
            logger.error(f"加载模板失败: {e}")
            return_data["msg"] = "系统错误：模板文件不存在"
            return return_data
            
        return_data["code"] = 200
   
        return return_data


    async def richang(self, mode: str, num: int) -> Dict[str, Any]:
        """活动日历"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            if mode == "list":
                today = data.get("today") or {}
                total = data.get("total") or []

                items = [
                    {
                        "en": False,
                        "compare": "",
                        "date": "",
                        "war": "",
                        "battle": "",
                    }
                    for _ in range(week_to_num(today.get("week", "")) or 0)
                ]

                items.extend(
                    {
                        "en": True,
                        "compare": compare_date_str(item.get("date", "")),
                        "date": item.get("date", ""),
                        "war": item.get("war", ""),
                        "battle": item.get("battle", ""),
                    }
                    for item in total
                    if isinstance(item, dict)
                )

                return_data["data"]["items"] = items
                return_data["data"]["today"] = today
                return

            weekly = data.get("weekly") or {}

            return_data["data"] = (
                f"{data.get('date', '')} 星期{data.get('week', '')}\n"
                f"大战：{data.get('war', '')}\n"
                f"战场：{data.get('battle', '')}\n"
                f"阵营：{data.get('orecar', '')}\n"
                f"宗门：{data.get('school', '')}\n"
                f"驰援：{data.get('rescue', '')}\n"
                f"【宠物福缘】\n{', '.join(data.get('lucky') or [])}\n"
                f"【家园声望·加倍道具】\n{', '.join(data.get('card') or [])}\n"
                f"【武林通鉴·公共任务】\n{', '.join(weekly.get('conn') or [])}\n"
                f"【武林通鉴·团队秘境】\n{', '.join(weekly.get('raid') or [])}\n"
            )

        return await self._request_api(
            path="/active/calendar",
            params={"mode": mode, "num": num},
            processor=processor,
            template="richangyuche.html" if mode == "list" else None,
        )

    
    async def xingxiashijian(self,name: str) -> Dict[str, Any]:
        """地图活动"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            return_data["data"]["items"] = data
            return_data["data"]["name"] = name

        return await self._request_api(
            path="/active/celebs",
            params={ "name": name},
            processor=processor,
            template="xingxiashijian.html"
        )


    async def guanaishouling(self) -> Dict[str, Any]:
        """关隘首领"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            groups = [
                {
                    "server": group.get("server", ""),
                    "records": [
                        {
                            "camp_name": item.get("campName", ""),
                            "castle": item.get("castle", ""),
                            "str_status": item.get("statusText", ""),
                            "start_time": format_time(item.get("startTime")),
                            "end_time": format_time(item.get("endTime")),
                            "remaining_time": format_remaining(item.get("endTime")),
                        }
                        for item in group.get("data", [])
                        if isinstance(item, dict)
                    ],
                }
                for group in data
                if isinstance(group, dict) and group.get("data")
            ]

            groups = [group for group in groups if group["records"]]

            if not groups:
                return_data["msg"] = "未查询到关隘首领信息"
                return return_data

            return_data["data"] = {
                "groups": groups,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        return await self._request_api(
            path="/castle/status",
            params={"token": self.token},
            processor=processor,
            template="guanaishouling.html"
        )


    async def benrichitu(self) -> Dict[str, Any]:
        """本日赤兔"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            if not data or not isinstance(data, list):
                return_data["data"] = "今日赤兔 暂无数据"
                return 
            
            result_lines = ["今日赤兔"]
            for item in data:
                result_lines.extend([
                    f"时间：{item['date']}",
                    f"区服：{item['server']}",
                    f"地图：{item['mapName']}",
                ])

            return_data["data"] = "\n".join(result_lines).rstrip()
            
        return await self._request_api(
            path="/chitu/records",
            params={"token": self.token},
            processor=processor,
            template=""
        )        


    async def benzhouchitu(self) -> Dict[str, Any]:
        """本周赤兔"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            if not data or not isinstance(data, list):
                return_data["data"] = "本周赤兔 暂无数据"
                return 
            
            result_lines = ["本周赤兔"]
            for item in data:
                result_lines.extend([
                    f"时间：{item['date']}",
                    f"区服：{item['server']}",
                    f"地图：{item['mapName']}",
                ])

            return_data["data"] = "\n".join(result_lines).rstrip()
            
        return await self._request_api(
            path="/chitu/week/records",
            params={"token": self.token},
            processor=processor,
            template=""
        )  


    async def zhenyingevent(self,name: str,limit: str) -> Dict[str, Any]:
        """阵营事件"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            for item in data:
                item["seizeTime"] = format_time(item.get("seizeTime"))

            return_data["data"] = {
                "items": data,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        return await self._request_api(
            path="/fenxian/records",
            params={"token": self.token,"name": name, "limit": limit},
            processor=processor,
            template="zhenyingevent.html"
        )  
            

    async def yanhuachaxun(self, server: str, name:str ) -> Dict[str, Any]:
        """烟花记录"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            for item in data:
                item["time"] = format_time(item.get("time"))

            return_data["data"]["list"] = data
            
        return await self._request_api(
            path="/firework/records",
            params={"token": self.token,"name": name, "server": server},
            processor=processor,
            template="yanhuan.html"
        )  


    async def shuma(self,server:str) -> Dict[str, Any]:
        """刷马"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:    
            return_data["data"] = (
                f"【阴山大草原】\n{', '.join(data.get('阴山大草原') or [])}\n"
                f"【鲲鹏岛】\n{', '.join(data.get('鲲鹏岛') or [])}\n"
                f"【黑戈壁】\n{', '.join(data.get('黑戈壁') or [])}\n"
            )
            
        return await self._request_api(
            path="/ranch/chat",
            params={"token": self.token, "server": server},
            processor=processor,
            template=""
        )  


    async def machang(self, server: str, expired: int) -> Dict[str, Any]:
        """马场"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            data0 = data.get("data") 
            return_data["data"] = (
                f"【区服】：{data.get('server')}\n"
                f"【阴山大草原】\n{', '.join(data0.get('阴山大草原') or [])}\n"
                f"【鲲鹏岛】\n{', '.join(data0.get('鲲鹏岛') or [])}\n"
                f"【黑戈壁】\n{', '.join(data0.get('黑戈壁') or [])}\n"
                f"【龙泉府 / 进图（21:10）】\n{', '.join(data0.get('龙泉府 / 进图（21:10）') or [])}\n"
                f"\n{data.get('note')}\n"
            )
            
        return await self._request_api(
            path="/ranch/records",
            params={"token": self.token, "server": server, "expired": expired},
            processor=processor,
            template=""
        )  


    async def zhanji(self, name: str, server:str, mode:str) -> Dict[str, Any]:
        """战绩"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = data
            
        return await self._request_api(
            path="/arena/recent",
            params={"server": server, "name":name, "mode":mode, "token": self.token, "ticket": self.ticket},
            processor=processor,
            template="zhanji.html"
        )  


    async def mingjianpaihang(self, limit: str, mode:str) -> Dict[str, Any]:
        """名剑排行"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"]["lists"] = data
            
        return await self._request_api(
            path="/arena/awesome",
            params={"limit": limit, "mode":mode, "token": self.token, "ticket": self.ticket},
            processor=processor,
            template="mingjianpaihang.html"
        )          


    async def mingjiantongji(self, mode: str) -> Dict[str, Any]:
        """名剑统计"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = {
                "items": data,
                "mode": mode,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        return await self._request_api(
            path="/arena/schools",
            params={"mode": mode, "token": self.token, "ticket": self.ticket},
            processor=processor,
            template="mingjiantongji.html"
        )         


    async def rank_statistical(self, name: str, server: str) -> Dict[str, Any]:
        """排行榜单"""
        ROLE_RANK_NAMES = {
            "名士五十强",
            "老江湖五十强",
            "兵甲藏家五十强",
            "名师五十强",
            "阵营英雄五十强",
            "薪火相传五十强",
            "庐园广记一百强",
        }
        TONG_RANK_NAMES0 = {
            "赛季恶人五十强",
            "赛季浩气五十强",
            "本周恶人五十强",
            "本周浩气五十强",
        }
        TONG_RANK_NAMES1 = {
            "浩气神兵宝甲五十强",
            "恶人神兵宝甲五十强",
            "浩气爱心帮会五十强",
            "恶人爱心帮会五十强",
        }
        TONG_RANK_NAMES2 = {
            "上周恶人五十强",
            "上周浩气五十强",
        }
        if name in ROLE_RANK_NAMES:
            template_name = "rank_role.html"
        elif name in TONG_RANK_NAMES0:
            template_name = "rank_tong0.html"
        elif name in TONG_RANK_NAMES1:
            template_name = "rank_tong1.html"
        elif name in TONG_RANK_NAMES2:
            template_name = "rank_tong2.html"

        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            items = data.get("data", [])

            return_data["data"] = {
                "items": items,
                "server": data.get("server", server),
                "rank_name": data.get("name", name),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        return await self._request_api(
            path="/rank/statistics",
            params={"server": server, "name": name, "token": self.token},
            processor=processor,
            template=template_name
        )   


    async def shilianpaixing(self, name: str, server: str) -> Dict[str, Any]:
        """试炼排行"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            items = data.get("data", [])

            return_data["data"] = {
                "items": items,
                "name": data.get("name", name),
                "server": data.get("server", server),
                "update_time": format_time(data.get("time"))
            }
            
        return await self._request_api(
            path="/rank/trials",
            params={"server": server,"name": name,"token": self.token,},
            processor=processor,
            template="shilianpaixing.html"
        )   


    async def zhengyingpaimai(self, server: str, name: str, limit: int) -> Dict[str, Any]:
        """阵营拍卖"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            for item in data:
                item["time"] =  format_time(item["time"])
            return_data["data"]["list"] = data
            
        return await self._request_api(
            path="/auction/records",
            params={"server": server, "name": name, "limit": limit, "token": self.token},
            processor=processor,
            template="zhengyingpaimai.html"
        )           


    async def dilujilu(self, server: str) -> Dict[str, Any]:
        """的卢拍卖"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            for item in data:
                item["refreshTime"] = format_time(item["refreshTime"]) 
                item["captureTime"] = format_time(item["captureTime"])
                item["auctionTime"] = format_time(item["auctionTime"])
            return_data["data"]["list"] = data
            
        return await self._request_api(
            path="/steed/records",
            params={"server": server, "token": self.token},
            processor=processor,
            template="dilujilu.html"
        ) 


    async def jinjia(self, server: str, limit:str) -> Dict[str, Any]:
        """金价行情"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"]["items"] = data
            
        return await self._request_api(
            path="/trade/demon",
            params={"server": server, "limit": limit, "token": self.token},
            processor=processor,
            template="jinjia.html"
        ) 


    async def wujia(self, Name: str, server:str) -> Dict[str, Any]:
        """物价查询"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = data
            
        return await self._request_api(
            path="/trade/records",
            params={"name": Name,"token": self.token, "server": server},
            processor=processor,
            template="wujia.html"
        ) 


    async def chengbeng(self, Name: str, server:str, source: int) -> Dict[str, Any]:
        """成本计算"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = data
            
        return await self._request_api(
            path="/trade/manufacture",
            params={"name": Name,"token": self.token, "server": server, "source": source},
            processor=processor,
            template="chengbeng.html"
        ) 

    async def bianhao(self, id: str) -> Dict[str, Any]:
        """编号搜索"""
        # 数据处理
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            if not isinstance(data, dict):
                return_data["data"] = "账号角色数据格式错误"
                return

            # 同时兼容完整接口数据和直接传入 data 字段
            data = data.get("data", data)

            if not isinstance(data, dict):
                return_data["data"] = "账号角色数据为空"
                return

            # 将 replyContent 中的 HTML 转换为纯文本
            detail = str(data.get("replyContent") or "")
            detail = re.sub(r"<br\s*/?>", "\n", detail, flags=re.IGNORECASE)
            detail = re.sub(r"<[^>]+>", "", detail)
            detail = html.unescape(detail).strip() or "暂无账号详细信息"

            # 交易状态
            trade_status = {
                1: "公示中",
                2: "出售中",
                3: "出售中",
                4: "已售出",
                5: "已下架",
            }.get(data.get("tradeStatus"), f"状态码 {data.get('tradeStatus', '未知')}")

            # 调价记录，接口中的时间为毫秒时间戳
            update_prices = data.get("updatePrices") or []
            update_price_text = "\n".join(
                f"{index}. {format_time(int(item.get('updateTime') or 0) // 1000)}："
                f"{item.get('updatePrice', 0)} 元"
                for index, item in enumerate(update_prices, start=1)
                if isinstance(item, dict)
            ) or "暂无调价记录"

            return_data["data"] = (
                f"【万宝楼账号】\n"
                f"{data.get('replyTitle') or '暂无标题'}\n\n"

                f"【角色信息】\n"
                f"区服：{data.get('serverName') or '未知'}\n"
                f"角色：{data.get('roleName') or '未知'}\n"
                f"等级：{data.get('roleLevel') or 0}\n"
                f"门派：{data.get('forceName') or '未知'}\n"
                f"体型：{data.get('bodyName') or '未知'}\n"
                f"阵营：{data.get('campName') or '未知'}\n\n"

                f"【账号数据】\n"
                f"装备分数：{data.get('equipScore') or 0}\n"
                f"江湖资历：{data.get('seniorityNum') or 0}\n"
                f"约见次数：{data.get('meetingNum') or 0}\n"
                f"关注人数：{data.get('followNum') or 0}\n\n"

                f"【交易信息】\n"
                f"挂牌价格：{data.get('priceNum') or 0} 元\n"
                f"交易状态：{trade_status}\n"
                f"商品编号：{data.get('id') or '未知'}\n"
                f"发布时间：{format_time(data.get('replyTime') or 0)}\n\n"

                f"【调价记录】\n"
                f"{update_price_text}\n\n"

                f"【账号详情】\n"
                f"{detail}"
            )
            
        return await self._request_api(
            path="/trade/wanbaolou",
            params={"id": id,"token": self.token},
            processor=processor,
            template=""
        ) 


    async def bangzhanjilu(self, server: str) -> Dict[str, Any]:
        """帮战记录"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            for item in data:
                item["startTime"] = format_time(item["startTime"])
                item["durationSeconds"] = format_remaining(item["durationSeconds"])
                item["endTime"] = format_time(item["endTime"])

            return_data["data"] = {
                "items": data,
                "server": server,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
        return await self._request_api(
            path="/battle/records",
            params={"server": server},
            processor=processor,
            template="bangzhanjilu.html"
        ) 


    async def zhueevent(self,server: str,limit: str) -> Dict[str, Any]:
        """诛恶事件"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            for item in data:
                item["time"] = format_time(item["time"])

            return_data["data"] = {
                "items": data,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        return await self._request_api(
            path="/wicked/records",
            params={"token": self.token, "server": server, "limit": limit},
            processor=processor,
            template="zhueevent.html"
        ) 


    async def jueshemingpian(self, server: str, name: str) -> Dict[str, Any]:
        """名片缓存"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            url = data.get("showAvatar")
            if not url:
                return_data["msg"] = "未获取到名片图片"
                return return_data

            server_name = data.get("serverName", server)
            role_name = data.get("roleName", name)
            show_like = data.get("showLike", 0)
            msg0 = f"{server_name}-{role_name}"
            msg1 = f"点赞：{show_like}"

            return_data["data"] = [
                Comp.Plain(msg0),
                Comp.Image.fromURL(url),
                Comp.Plain(msg1)
            ]
            
        return await self._request_api(
            path="/card/cached",
            params={"server": server, "name": name, "token": self.token},
            processor=processor,
            template=""
        ) 


    async def shuijimingpian(self, server:str, force: str, body:str,) -> Dict[str, Any]:
        """随机名片"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            url = data.get("showAvatar")
            if not url:
                return_data["msg"] = "未获取到名片图片"
                return return_data

            server_name = data.get("serverName")
            role_name = data.get("roleName")
            msg = f"{server_name}-{role_name}"

            return_data["data"] = [
                Comp.Plain(msg),
                Comp.Image.fromURL(url),
            ]
            
        return await self._request_api(
            path="/card/random",
            params={"server": server, "body": body, "force":force, "token": self.token},
            processor=processor,
            template=""
        ) 


    async def shuoyoumingpian(self, server: str, name: str) -> Dict[str, Any]:
        """名片历史"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            chain = []
            for m in data:
                status = "当前展示" if m.get("showActive") else "未展示"
                msg = f"第{m.get('showIndex')}张 {status}"
                url = m.get("showAvatar")

                if not url:
                    logger.warning(f"第{m.get('showIndex')}张名片缺少图片URL，已跳过")
                    continue

                chain.extend([
                    Comp.Plain(msg),
                    Comp.Image.fromURL(url),
                ])

            if not chain:
                return_data["msg"] = "未获取到有效的名片数据"
                return return_data

            return_data["data"] = chain

        return await self._request_api(
            path="/card/records",
            params={"server": server, "name": name, "token": self.token},
            processor=processor,
            template=""
        ) 


    async def qiyuhuizong(self, server: str, num: int) -> Dict[str, Any]:
        """奇遇汇总"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            for item in data:
                latest = item.get("last")
                item["latest_name"] = latest.get("name")
                item["latest_time"] = format_time(latest.get("time"))

            return_data["data"] = {
                "items": data,
                "server": server,
                "num": num,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        return await self._request_api(
            path="/event/collect",
            params={"server": server, "num": num, "token": self.token},
            processor=processor,
            template="qiyuhuizong.html"
        ) 


    async def weizuoqiyu(self, server: str, name: str, ) -> Dict[str, Any]:
        """未出奇遇"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"]["ptqy"] = []
            return_data["data"]["jsqy"] = []
            return_data["data"]["name"] = name
            return_data["data"]["server"] = server

            for item in data:
                try:
                    level = int(item.get("level", 0))
                except (TypeError, ValueError):
                    continue

                event_item = {
                    "event": item.get("name"),
                    "time": "未触发"
                }

                if level == 1:
                    return_data["data"]["ptqy"].append(event_item)
                elif level == 2:
                    return_data["data"]["jsqy"].append(event_item)

            if not return_data["data"]["ptqy"] and not return_data["data"]["jsqy"]:
                return_data["msg"] = "未查询到未做普通或绝世奇遇"
                return return_data
            
        return await self._request_api(
            path="/event/missing",
            params={"server": server, "name": name, "token": self.token},
            processor=processor,
            template="weizuoqiyu.html"
        ) 


    async def jinqiqiyu(self, server: str, limit: int) -> Dict[str, Any]:
        """近期奇遇"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            for item in data:
                item["time"] = format_time(item.get("time"))

            return_data["data"] = {
                "items": data,
                "server": server,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        return await self._request_api(
            path="/event/recent",
            params={"server": server, "limit": limit, "token": self.token},
            processor=processor,
            template="jinqiqiyu.html"
        ) 

    
    async def juesheqiyu(self, server: str, name: str, full: int) -> Dict[str, Any]:
        """角色奇遇"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"]["ptqy"] = []
            return_data["data"]["jsqy"] = []
            return_data["data"]["cwqy"] = []

            for item in data:
                item["time"] = datetime.fromtimestamp(item["time"]).strftime("%Y-%m-%d %H:%M:%S")
                if item["level"] == 1:
                    return_data["data"]["ptqy"].append(item)
                if item["level"] == 2:
                    return_data["data"]["jsqy"].append(item)
                if item["level"] == 3:
                    return_data["data"]["cwqy"].append(item)
            
        return await self._request_api(
            path="/event/records",
            params= {"server": server, "name": name, "full": full, "token": self.token},
            processor=processor,
            template="juesheqiyu.html"
        ) 


    async def qiyutongji(self, name: str, server: str, limit: int) -> Dict[str, Any]:
        """奇遇统计"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            for item in data:
                item["time"] = format_time(item.get("time"))

            return_data["data"] = {
                "items": data,
                "server": server,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "qiyuname": name
            }

        return await self._request_api(
            path="/event/statistics",
            params={"name": name, "server": server, "limit": limit, "token": self.token},
            processor=processor,
            template="qiyuliebiao.html"
        ) 


    async def jingnai(self, name: str, server: str) -> Dict[str, Any]:
        """角色百战"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            items = data.get("skillList", [])
            if not isinstance(items, list) or not items:
                return_data["msg"] = "未查询到技能信息"
                return return_data

            color_map = {
                7: "黑色",
                6: "紫色",
                5: "红色",
                4: "绿色",
                3: "蓝色",
                2: "黄色",
                0: "无",
            }

            for item in items:
                if not isinstance(item, dict):
                    continue

                color = item.get("nColor")
                try:
                    color_key = int(color)
                except (TypeError, ValueError):
                    color_key = None
                item["skill_color_text"] = color_map.get(color_key, str(color) if color is not None else "")

            return_data["data"] = {
                "server": data.get("server", server),
                "role_name": data.get("roleName", name),
                "skill_energy": data.get("skillEnergy", ""),
                "skill_stamina": data.get("skillStamina", ""),
                "skill_count": data.get("skillCount", len(items)),
                "items": items,
                "update_time": format_time( data.get("updateTime"))
            }

        return await self._request_api(
            path="/monster/records",
            params={"server": server, "name": name, "token": self.token},
            processor=processor,
            template="jingnai.html"
        ) 


    async def baizhan(self) -> Dict[str, Any]:
        """百战首领"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = data
            return_data["data"]["start"]  = format_time(data["start"])   
            return_data["data"]["end"]  = format_time(data["end"])   

        return await self._request_api(
            path="/monster/weekly",
            params= { "token": self.token},
            processor=processor,
            template="baizhan.html"
        ) 


    async def chengjiuchaxun(self, server:str, role:str, name:str) -> Dict[str, Any]:
        """成就查询"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = data

        return await self._request_api(
            path="/role/achievement",
            params= {"server": server, "role": role, "name": name, "token": self.token},
            processor=processor,
            template="chengjiu.html"
        ) 


    async def jueshe(self,server: str, name: str, history:int) -> Dict[str, Any]:
        """角色详情"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            role_history = data.get("roleHistory") or {}
            role_names = role_history.get("roleNames") or []
            tong_names = role_history.get("TongNames") or []

            # 角色名称历史
            role_history_lines = []

            for item in role_names:
                if not isinstance(item, dict):
                    continue

                server = item.get("server") or "未知服务器"
                name = item.get("name") or "未知角色名"
                time_text = format_time(item.get("time", 0))

                role_history_lines.append(
                    f"{time_text}　{server}·{name}"
                )

            if role_history_lines:
                role_history_text = "\n".join(role_history_lines)
            else:
                role_history_text = "暂无角色历史记录"

            # 帮会历史
            tong_history_lines = []

            for item in tong_names:
                if not isinstance(item, dict):
                    continue

                server = item.get("server") or "未知服务器"
                tong_name = item.get("name") or "无帮会"
                time_text = format_time(item.get("time", 0))

                tong_history_lines.append(
                    f"{time_text}　{server}·{tong_name}"
                )

            if tong_history_lines:
                tong_history_text = "\n".join(tong_history_lines)
            else:
                tong_history_text = "暂无帮会历史记录"

            return_data["data"] = (
                f"服务器：{data.get('zoneName') or '未知'}·"
                f"{data.get('serverName') or '未知'}\n"
                f"名称：{data.get('roleName') or '未知'}\n"
                f"角色ID：{data.get('roleId') or '未知'}\n"
                f"推栏ID：{data.get('globalId') or '未知'}\n"
                f"职业：{data.get('forceName') or '未知'}·"
                f"{data.get('bodyName') or '未知'}\n"
                f"帮会：{data.get('tongName') or '无帮会'}\n"
                f"阵营：{data.get('campName') or '未知'}\n"
                f"\n"
                f"【角色历史】\n"
                f"{role_history_text}\n"
                f"\n"
                f"【帮会历史】\n"
                f"{tong_history_text}"
            )

        return await self._request_api(
            path="/role/detail",
            params= {"server": server, "name": name, "history": history, "token": self.token},
            processor=processor,
            template=""
        ) 


    async def zhenyan(self, name: str) -> Dict[str, Any]:
        """阵眼"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            items = data.get("data", [])
            if not isinstance(items, list) or not items:
                return_data["msg"] = "未查询到该心法阵眼信息"
                return return_data

            result_msg = f"{data.get('name', name)}-{data.get('skillName', '')}\n"
            for item in items:
                if not isinstance(item, dict):
                    continue
                result_msg += f"{item.get('name', '')}：{item.get('desc', '')}\n"

            return_data["data"] = result_msg.rstrip()

        return await self._request_api(
            path="/school/matrix",
            params= {"name": name, "ticket": self.ticket, "token": self.token},
            processor=processor,
            template=""
        ) 


    async def zilipaixing(self,server: str, school: str) -> Dict[str, Any]:
        """资历排行"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = {
                "items": data,
                "school": school,
                "server": server,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        return await self._request_api(
            path="/school/seniority",
            params= {"server": server,"school": school,"ticket": self.ticket,"token": self.token,},
            processor=processor,
            template="zilipaixing.html"
        ) 


    async def jineng(self, name: str,update:int) -> Dict[str, Any]:
        """技能"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            groups = []
            for group in data:
                if not isinstance(group, dict):
                    continue

                skills = group.get("data", [])
                if not isinstance(skills, list) or not skills:
                    continue

                parsed_skills = []
                for skill in skills:
                    if not isinstance(skill, dict):
                        continue

                    parsed_skills.append({
                        "name": skill.get("name", ""),
                        "icon": skill.get("icon", ""),
                        "desc": skill.get("desc", ""),
                        "interval": skill.get("interval", ""),
                        "distance": skill.get("distance", ""),
                        "release_type": skill.get("releaseType", ""),
                        "weapon": skill.get("weapon", ""),
                    })

                if parsed_skills:
                    groups.append({
                        "title": group.get("class", "其他技能"),
                        "skills": parsed_skills,
                    })

            if not groups:
                return_data["msg"] = "未查询到该心法技能信息"
                return return_data

            return_data["data"] = {
                "name": name,
                "groups": groups,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        return await self._request_api(
            path="/school/skills",
            params= {"name": name,"update": update, "ticket": self.ticket, "token": self.token},
            processor=processor,
            template="jineng.html"
        ) 


    async def qixue(self, name: str, update:int) -> Dict[str, Any]:
        """奇穴"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            level_titles = {
                1: "主奇穴",
                2: "第一重",
                3: "第二重",
                4: "第三重",
                5: "第四重",
                6: "第五重",
                7: "第六重",
                8: "混池",
            }

            groups = []
            for group in data:
                if not isinstance(group, dict):
                    continue

                level = group.get("level")
                try:
                    level_key = int(level)
                except (TypeError, ValueError):
                    level_key = 0

                items = group.get("data", [])
                if not isinstance(items, list) or not items:
                    continue

                parsed_items = []
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    class_value = item.get("class")
                    is_active = class_value == 1 or str(class_value) == "1"
                    parsed_items.append({
                        "name": item.get("name", ""),
                        "icon": item.get("icon", ""),
                        "desc": item.get("desc", ""),
                        "class_text": "主动" if is_active else "被动",
                        "interval": item.get("interval", "") if is_active else "",
                    })

                if parsed_items:
                    groups.append({
                        "level": level_key,
                        "title": level_titles.get(level_key, f"第{level_key}组"),
                        "talents": parsed_items,
                    })

            if not groups:
                return_data["msg"] = "未查询到该心法奇穴信息"
                return return_data

            groups.sort(key=lambda item: item["level"])
            return_data["data"] = {
                "name": name,
                "groups": groups,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        return await self._request_api(
            path="/school/talent",
            params= {"name": name,"update": update, "ticket": self.ticket, "token": self.token},
            processor=processor,
            template="qixue.html"
        ) 


    async def juesheliaotian(self, server:str, name: str, limit:int, page:int) -> Dict[str, Any]:
        """角色聊天"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            chat_list = data.get("list", [])

            for item in chat_list:
                item["time"] = format_time(item.get("time", 0))

            return_data["data"] = data

        return await self._request_api(
            path="/chat/records",
            params= {"server": server,"name": name, "limit": limit, "page": page, "token": self.token},
            processor=processor,
            template="juesheliaotian.html"
        ) 


    async def tongzhanyy(self, server: str) -> Dict[str, Any]:
        """统战歪歪"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            lines = ["【统战歪歪】"]
            for group in data:
                group_server = group.get("server", "")
                channels = group.get("data", [])

                if len(lines) > 1:
                    lines.append("")
                lines.append(f"服务器：{group_server}")

                for item in channels:
                    if not isinstance(item, dict):
                        continue

                    short_id = item.get("esid") or item.get("asid", "")
                    lines.extend([
                        f"阵营：{item.get('campName', '')}",
                        f"频道ID：{item.get('sid', '')}",
                        f"短位ID：{short_id}",
                        f"在线人数：{item.get('users', '')}",
                        f"频道名：{item.get('snick', '')}",
                        "",
                    ])

                    return_data["data"] = "\n".join(lines)

        return await self._request_api(
            path="/duowan/statistics",
            params= {"server": server},
            processor=processor,
            template=""
        ) 


    async def xiaoyao(self, name:str) -> Dict[str, Any]:
        """小吃小药"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            result = {}

            for item in data:
                k = item["kungfu"]
                color = item["color"]
                cls = item["class"]
                name = item["name"]

                if k not in result:
                    result[k] = {
                        "kungfu": k,
                        "purple": {},
                        "blue": {}
                    }

                if color == "紫":
                    result[k]["purple"][cls] = name
                else:
                    result[k]["blue"][cls] = name

            return_data["data"]["items"] = list(result.values())

        return await self._request_api(
            path="/food/list",
            params= {"name": name},
            processor=processor,
            template="xiaoyao.html"
        ) 


    async def pianzhi(self, server:str, uid: str) -> Dict[str, Any]:
        """骗子查询"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            records = data["records"]

            if not records:
                result_msg = "未找到该用户行骗记录，很棒！继续保持！"
            else:
                result_msg = ""

                for record in records:
                    result_msg += f"区服：{record['server']}  标签：{record['tieba']}\n\n"

                    for item in record["data"]:
                        result_msg += f"标题：{item['title']}\n"
                        result_msg += f"地址：{item['url']}\n"
                        result_msg += f"ID：{item['tid']}\n"
                        result_msg += f"内容：{item['text']}\n"
                        result_msg += (
                            f"时间：{datetime.fromtimestamp(item['time']).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        )

                    result_msg += "\n\n"
            return_data["data"] = result_msg

        return await self._request_api(
            path="/fraud/detail",
            params= {"server": server, "uid": uid, "token": self.token},
            processor=processor,
            template=""
        ) 


    async def huajia(self,server: str, name: str, map: str) -> Dict[str, Any]:
        """家园鲜花"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"]["data"] = data
            return_data["data"]["server"] = server

        return await self._request_api(
            path="/home/flower",
            params= {"server": server, "name": name,  "map": map},
            processor=processor,
            template="huajia.html"
        ) 


    async def zhuangshi(self,name: str) -> Dict[str, Any]:
        """家园装饰"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"]["data"] = data

        return await self._request_api(
            path="/home/furniture",
            params= { "name": name},
            processor=processor,
            template="zhuangshi.html"
        ) 


    async def qiwu(self,name: str) -> Dict[str, Any]:
        """器物图谱"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"]["data"] = data
            return_data["data"]["name"] = name

        return await self._request_api(
            path="/home/travel",
            params= { "name": name},
            processor=processor,
            template="qiwu.html"
        ) 
 

    async def shitu(self, label: int, server: str, keyword: str, limit:int) -> Dict[str, Any]:
        """师徒招募"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            items = data
            if not items:
                return_data["msg"] = "未查询到师徒招募信息"
                return return_data

            title = "收徒信息" if label == 1 else "拜师信息"
            return_data["data"] = {
                "items": items,
                "server": server,
                "keyword": keyword,
                "type_value": label,
                "title": title,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        return await self._request_api(
            path="/mentor/search",
            params= {"label": label, "server": server, "keyword": keyword, "limit": limit, "token": self.token},
            processor=processor,
            template="shitu.html"
        ) 


    async def weihu(self, limit:int) -> Dict[str, Any]:
        """维护公告"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            result = data[0]
            return_data["status"] = result.get('id')

            result_msg = "维护推送\n"
            # 仅展示前1条，避免消息过长
            for i, item in enumerate(data[:limit], 1): 
                result_msg += f"{i}. 【{item.get('type', '无类型')}】\n"
                result_msg += f"标题：{item.get('title', '未知时间')}\n"
                result_msg += f"时间：{item.get('date', '未知时间')}\n"
                result_msg += f"链接：{item.get('url', '无链接')}\n"
                
            return_data["data"] = result_msg

        return await self._request_api(
            path="/news/announce",
            params= {"limit": limit},
            processor=processor,
            template=""
        ) 


    async def xinwen(self, limit:int) -> Dict[str, Any]:
        """新闻资讯"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            result = data[0]
            return_data["status"] = int(result.get('catid'))

            result_msg = "新闻资讯推送\n"
            # 仅展示前1条，避免消息过长
            for i, item in enumerate(data[:limit], 1): 
                result_msg += f"{i}. 【{item.get('type', '无类型')}】\n"
                result_msg += f"标题：{item.get('title', '未知时间')}\n"
                result_msg += f"时间：{item.get('date', '未知时间')}\n"
                result_msg += f"链接：{item.get('url', '无链接')}\n"
                
            return_data["data"] = result_msg

        return await self._request_api(
            path="/news/records",
            params= {"limit": limit},
            processor=processor,
            template=""
        ) 


    async def tuanduizhaomu(self, server: str, label:int, keyword: str, limit:int) -> Dict[str, Any]:
        """团队招募"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            for item in data:
                item["createTime"] = format_time(item["createTime"])   
                item["maxMemberCount"] = f"{item['currentMemberCount']}/{item['maxMemberCount']}"
                return_data["data"]["list"] = data

        return await self._request_api(
            path="/recruit/search",
            params= {"server": server, "label": label, "keyword": keyword, "limit": limit, "token": self.token},
            processor=processor,
            template="tuanduizhaomu.html"
        ) 


    async def daanzhishu(self) -> Dict[str, Any]:
        """答案之书"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = (
                f"答案：{data.get('answer', '')}\n"
                f"鼓励：{data.get('hearten', '')}\n"
            )

        return await self._request_api(
            path="/saohua/answer",
            params= {},
            processor=processor,
            template=""
        ) 


    async def tiangou(self) -> Dict[str, Any]:
        """舔狗日志"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = data.get('text')

        return await self._request_api(
            path="/saohua/content",
            params= {},
            processor=processor,
            template=""
        ) 


    async def heshengme(self) -> Dict[str, Any]:
        """喝什么"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = (
                f"{', '.join(data or [])}\n"
            )

        return await self._request_api(
            path="/saohua/drink",
            params= {},
            processor=processor,
            template=""
        ) 


    async def chishengme(self) -> Dict[str, Any]:
        """吃什么"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = (
                f"{', '.join(data or [])}\n"
            )

        return await self._request_api(
            path="/saohua/eat",
            params= {},
            processor=processor,
            template=""
        ) 


    async def shaohua(self) -> Dict[str, Any]:
        """随机骚话"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = data.get('text')

        return await self._request_api(
            path="/saohua/random",
            params= {},
            processor=processor,
            template=""
        ) 


    async def zhananyulu(self) -> Dict[str, Any]:
        """渣男语录"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"] = data.get('text')

        return await self._request_api(
            path="/saohua/zhanan",
            params= {},
            processor=processor,
            template=""
        ) 


    async def keju(self,subject: str, limit: int) -> Dict[str, Any]:
        """科举"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            result_msg = ""
            for m in data:
                result_msg += f"{m['id']}.{m['question']}\n"
                result_msg += f"答案：{m['answer']}\n\n"

            return_data["data"] = result_msg

        return await self._request_api(
            path="/exam/search",
            params= {"subject": subject, "limit": limit},
            processor=processor,
            template=""
        ) 


    async def zhuangtai(self,server:str) -> Dict[str, Any]:
        """区服状态"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            server_wj = []
            server_dx = []
            server_sx = []

            for itme in data:
                if itme['zone'] == "无界区":
                    server_wj.append(itme)
                elif itme['zone'] == "电信区":
                    server_dx.append(itme)
                elif itme['zone'] == "双线区":
                    server_sx.append(itme)

            return_data["data"]["server_wj"] = server_wj
            return_data["data"]["server_dx"] = server_dx
            return_data["data"]["server_sx"] = server_sx

        return await self._request_api(
            path="/server/status/check",
            params= {"server": server, "type": "其他"},
            processor=processor,
            template="qufuzhuangtai.html"
        ) 


    async def kaifu(self, server: str) -> Dict[str, Any]:
        """开服状态查询"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            list_data = data[0]
            status = list_data.get("status")
            
            if status == 1:
                status_str = f"{server}服务器已开服，快冲，快冲！"
                status_bool = True
            else:
                status_str = f"{server}服务器当前维护中，等会再来吧！"
                status_bool = False

            return_data["status"] = status_bool
            return_data["data"] = status_str

        return await self._request_api(
            path="/server/status/check",
            params= {"server": server, "type": 1},
            processor=processor,
            template="qufuzhuangtai.html"
        ) 


    async def jigai(self) -> Dict[str, Any]:
        """技改记录"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            result_msg = "最近技改\n"
            
            for i, item in enumerate(data[:3], 1): 
                result_msg += f"{i}. {item.get('title', '无标题')}\n"
                result_msg += f"时间：{item.get('time', '未知时间')}\n"
                result_msg += f"链接：{item.get('url', '无链接')}\n\n"
                
            return_data["data"] = result_msg

        return await self._request_api(
            path="/skill/rework",
            params= {},
            processor=processor,
            template=""
        ) 


    async def diaoluo(self, name: str, server: str, limit: int ) -> Dict[str, Any]:
        """物品掉落记录"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            for item in data:
                item["time"] = format_time(item.get("time"))

            return_data["data"] = {
                "items": data,
                "name": name,
                "limit": limit,
                "server": server,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        return await self._request_api(
            path="/reward/statistics",
            params= {"server": server, "name": name, "limit": limit, "token": self.token},
            processor=processor,
            template="diaoluo.html"
        ) 




    async def tiebawujia(self, name: str, server: str, limit: int ) -> Dict[str, Any]:
        """贴吧物价"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            lines = [
                f"贴吧物价：{name}",
                f"服务器：{server}",
                f"记录数：{len(data)}",
                "",
            ]

            for index, item in enumerate(data, start=1):
                if not isinstance(item, dict):
                    continue

                item_time = item.get("time", "")
                if item_time:
                    try:
                        item_time = datetime.fromtimestamp(int(item_time)).strftime("%Y-%m-%d %H:%M:%S")
                    except (TypeError, ValueError, OSError):
                        item_time = str(item_time)

                lines.extend([
                    f"{index}. {item.get('name', '')}",
                    f"区服：{item.get('zone', '')}  服务器：{item.get('server', '')}",
                    f"内容：{item.get('context', '')}",
                    f"回复：{item.get('reply', '')}  楼层：{item.get('floor', '')}",
                    f"时间：{item_time}",
                    f"链接：https://tieba.baidu.com/p/{item.get('url', '')}",
                    "",
                ])

            if len(lines) <= 4:
                return_data["msg"] = "未查询到贴吧物价记录"
                return return_data

            return_data["data"] = "\n".join(lines).rstrip()

        return await self._request_api(
            path="/tieba/item/records",
            params= {"server": server,"name": name,"limit": limit,"token": self.token,},
            processor=processor,
            template=""
        ) 


    async def bagua(self, tags: str, server:str, limit:str ) -> Dict[str, Any]:
        """八卦"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            if not data:
                result_msg = f"未找到相关 {tags} 记录。\n"
                result_msg += f"可选范围：818 616 鬼网三 鬼网3 树洞 记录 教程 街拍 故事 避雷 吐槽 提问"
            else:
                result_msg = f"类型：【{tags}】\n\n"

                for item in data:
                    result_msg += f"{item['title']}\n"
                    result_msg += f"服务器：{item['server']}\n"
                    result_msg += f"所属吧：{item['name']}\n"
                    result_msg += f"链接：https://tieba.baidu.com/p/{item['url']}\n"
                    result_msg += f"日期：{item['date']}\n\n"
            return_data["data"] = result_msg

        return await self._request_api(
            path="/tieba/random",
            params= {"server": server,"tags": tags,"limit": limit,"token": self.token,},
            processor=processor,
            template=""
        ) 


    async def fubengjilu(self, server:str, name: str ) -> Dict[str, Any]:
        """副本记录"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:   
            return_data["data"]["list"] = data

        return await self._request_api(
            path="/raid/records",
            params= {"server": server,"name": name,"token": self.token,},
            processor=processor,
            template="fubenjilu.html"
        ) 
    


    


    
        



    async def kuafumingjian(self, server: str = "", mode: str = "33") -> Dict[str, Any]:
        """跨服名剑"""
        mode_code = self._arena_mode_code(mode)
        mode_name = {0: "2v2", 1: "3v3", 2: "5v5"}.get(mode_code, "3v3")

        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            rows = []
            for index, item in enumerate(items, 1):
                rows.append([
                    self._pick(item, "rankNum", "rank", "nRank", default=str(index)),
                    self._pick(item, "roleName", "name", "role_name"),
                    self._pick(item, "forceName", "force", "school"),
                    self._pick(item, "serverName", "server", "zoneName"),
                    self._pick(item, "score", "totalScore", "value"),
                    self._pick(item, "winRate", "win_rate"),
                ])
            title = f"跨服名剑 {mode_name}"
            subtitle = f"{server or '全服'} · 更新时间：{self._now_text()}"
            self._set_table(return_data, title, ["排名", "角色", "门派", "区服", "分数", "胜率"], rows, subtitle, "暂无排行数据")

        params = {"mode": mode_code, "token": self.token}
        if server:
            params["server"] = server
        return await self._request_api("/rank/arena", params, processor, "data_list.html")

    async def wulinzhengba(self, server: str = "", camp: str = "浩气") -> Dict[str, Any]:
        """武林争霸"""
        camp_code = self._camp_code(camp)
        camp_name = "恶人谷" if camp_code == 2 else "浩气盟"

        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            rows = []
            for index, item in enumerate(items, 1):
                rows.append([
                    self._pick(item, "rankNum", "rank", default=str(index)),
                    self._pick(item, "tongName", "tong_name", "name"),
                    self._pick(item, "masterName", "master_name"),
                    self._pick(item, "serverName", "server"),
                    self._pick(item, "score", "totalScore", "titlePoint", "value"),
                ])
            title = f"武林争霸 {camp_name}"
            subtitle = f"{server or '全服'} · 更新时间：{self._now_text()}"
            self._set_table(return_data, title, ["排名", "帮会", "帮主", "区服", "积分"], rows, subtitle, "暂无排行数据")

        params = {"camp": camp_code, "token": self.token}
        if server:
            params["server"] = server
        return await self._request_api("/rank/championship", params, processor, "data_list.html")

    async def bukuai(self, server: str = "") -> Dict[str, Any]:
        """捕快荣誉"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            rows = []
            for index, item in enumerate(items, 1):
                rows.append([
                    self._pick(item, "rankNum", "rank", default=str(index)),
                    self._pick(item, "roleName", "name", "role_name"),
                    self._pick(item, "forceName", "force"),
                    self._pick(item, "serverName", "server"),
                    self._pick(item, "score", "totalScore", "value", "bounty"),
                ])
            subtitle = f"{server or '全服'} · 更新时间：{self._now_text()}"
            self._set_table(return_data, "捕快荣誉", ["排名", "角色", "门派", "区服", "积分"], rows, subtitle, "暂无排行数据")

        params = {"token": self.token}
        if server:
            params["server"] = server
        return await self._request_api("/rank/constable", params, processor, "data_list.html")

    async def langke(self, server: str = "") -> Dict[str, Any]:
        """江湖浪客"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            rows = []
            for index, item in enumerate(items, 1):
                rows.append([
                    self._pick(item, "rankNum", "rank", default=str(index)),
                    self._pick(item, "roleName", "name", "role_name"),
                    self._pick(item, "forceName", "force"),
                    self._pick(item, "serverName", "server"),
                    self._pick(item, "score", "totalScore", "value", "bounty"),
                ])
            subtitle = f"{server or '全服'} · 更新时间：{self._now_text()}"
            self._set_table(return_data, "江湖浪客", ["排名", "角色", "门派", "区服", "积分"], rows, subtitle, "暂无排行数据")

        params = {"token": self.token}
        if server:
            params["server"] = server
        return await self._request_api("/rank/outlaw", params, processor, "data_list.html")

    async def juedou(self, server: str = "", mode: str = "公开") -> Dict[str, Any]:
        """决斗挑战"""
        mode_code = self._wanted_mode(mode)
        mode_name = "私密" if mode_code == 2 else "公开"

        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            rows = []
            for index, item in enumerate(items, 1):
                rows.append([
                    self._pick(item, "rankNum", "rank", default=str(index)),
                    self._pick(item, "roleName", "name", "role_name"),
                    self._pick(item, "forceName", "force"),
                    self._pick(item, "serverName", "server"),
                    self._pick(item, "score", "totalScore", "value", "bounty"),
                ])
            title = f"决斗挑战 {mode_name}"
            subtitle = f"{server or '全服'} · 更新时间：{self._now_text()}"
            self._set_table(return_data, title, ["排名", "角色", "门派", "区服", "积分"], rows, subtitle, "暂无排行数据")

        params = {"mode": mode_code, "token": self.token}
        if server:
            params["server"] = server
        return await self._request_api("/rank/wanted", params, processor, "data_list.html")

    async def zilifenbu(self, server: str, name: str, class_id: str = "1", subclass: str = "") -> Dict[str, Any]:
        """资历分布"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            payload = data if isinstance(data, dict) else {}
            items = self._as_list(payload.get("data", payload))
            rows = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                total = item.get("total") or item.get("totalScore") or item.get("total_points") or 0
                done = item.get("speed") or item.get("completed") or item.get("completed_points") or 0
                rows.append([
                    self._pick(item, "name", "subClass", "subclass", "detail"),
                    str(done),
                    str(total),
                    self._pick(item, "percent", "percent_text", default=""),
                ])
            role = self._pick(payload, "roleName", "name", default=name)
            title = f"{role} 资历分布"
            subtitle = f"{server} · 更新时间：{self._now_text()}"
            self._set_table(return_data, title, ["分类", "已完成", "总计", "进度"], rows, subtitle, "暂无资历分布数据")

        params = {"server": server, "name": name, "class": class_id, "token": self.token, "ticket": self.ticket}
        if subclass:
            params["subclass"] = subclass
        return await self._request_api("/tuilan/achievement", params, processor, "data_list.html")

    async def waiguansousuo(self, name: str) -> Dict[str, Any]:
        """外观搜索"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            rows = []
            for item in items:
                rows.append([
                    self._pick(item, "name"),
                    self._pick(item, "alias", "wblalias"),
                    self._pick(item, "class", "subclass"),
                    self._pick(item, "value"),
                    self._pick(item, "date"),
                ])
            subtitle = f"关键词：{name} · 更新时间：{self._now_text()}"
            self._set_table(return_data, "外观搜索", ["名称", "别名", "分类", "参考价", "时间"], rows, subtitle, "暂无外观搜索结果")

        return await self._request_api("/trade/item/search", {"name": name, "token": self.token}, processor, "data_list.html")

    async def shapan(self, server: str) -> Dict[str, Any]:
        """沙盘据点"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            payload = data if isinstance(data, dict) else {}
            items = self._as_list(payload)
            rows = []
            for item in items:
                rows.append([
                    self._pick(item, "castleName", "castle_name"),
                    self._pick(item, "tongName", "tong_name"),
                    self._pick(item, "campName", "camp_name"),
                    self._pick(item, "masterName", "master_name"),
                    self._pick(item, "defend", "sacrifice", "count", default=""),
                ])
            title = f"{self._pick(payload, 'server', default=server)} 沙盘据点"
            subtitle = f"更新时间：{format_time(payload.get('update')) or self._now_text()}"
            self._set_table(return_data, title, ["据点", "帮会", "阵营", "帮主", "防守"], rows, subtitle, "暂无沙盘数据")

        return await self._request_api("/sand/records", {"server": server, "token": self.token}, processor, "data_list.html")

    async def mingpianyushe(self, server: str, name: str) -> Dict[str, Any]:
        """名片预设"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            payload = data if isinstance(data, dict) else {}
            url = payload.get("showAvatar") or payload.get("url") or payload.get("preset")
            if not url:
                return_data["msg"] = "未获取到名片预设图"
                return
            role = self._pick(payload, "roleName", default=name)
            server_name = self._pick(payload, "serverName", default=server)
            like = self._pick(payload, "showLike", "like", default="0")
            return_data["data"] = [
                Comp.Plain(f"{server_name}-{role}"),
                Comp.Image.fromURL(url),
                Comp.Plain(f"点赞：{like}"),
            ]

        return await self._request_api(
            "/card/preset",
            {"server": server, "name": name, "token": self.token, "ticket": self.ticket},
            processor,
            "",
        )

    async def qiyugonglue(self, name: str) -> Dict[str, Any]:
        """奇遇攻略"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            payload = data if isinstance(data, dict) else {"name": name, "desc": str(data or "")}
            rows = []
            if isinstance(payload, dict):
                for key, label in (
                    ("name", "名称"),
                    ("level", "等级"),
                    ("type", "类型"),
                    ("method", "触发"),
                    ("desc", "说明"),
                    ("note", "备注"),
                    ("reward", "奖励"),
                ):
                    value = payload.get(key)
                    if value not in (None, ""):
                        rows.append([label, str(value)])
                extras = payload.get("data") or payload.get("list")
                if isinstance(extras, list):
                    for item in extras:
                        rows.append([
                            self._pick(item, "name", "title", default="条目"),
                            self._pick(item, "desc", "text", "value"),
                        ])
            self._set_table(return_data, f"{name} 奇遇攻略", ["项目", "内容"], rows, empty_msg="暂无攻略内容")

        return await self._request_api("/event/strategy", {"name": name, "token": self.token}, processor, "data_list.html")

    async def peizhuang(self, name: str, tags: str = "") -> Dict[str, Any]:
        """配装搜索"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            if not items and isinstance(data, dict):
                items = [data]
            lines = [f"{name} 配装"]
            if tags:
                lines[0] += f"（{tags}）"
            for item in items:
                title = self._pick(item, "title", "name", "zlp", default="配装")
                url = self._pick(item, "url", "link", "href")
                mode = self._pick(item, "mode", "tags", "type")
                piece = f"【{mode}】{title}" if mode else title
                if url:
                    piece += f"\n{url}"
                lines.append(piece)
            return_data["data"] = "\n\n".join(lines) if len(lines) > 1 else f"{name} 暂无配装结果"

        params = {"name": name, "token": self.token, "ticket": self.ticket}
        if tags:
            params["mode"] = tags
        return await self._request_api("/school/search", params, processor, "")

    async def jisuji(self, cooldown: float = 1.5) -> Dict[str, Any]:
        """急速计算"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            if not items and isinstance(data, dict):
                maybe = data.get("list") or data.get("data")
                items = maybe if isinstance(maybe, list) else [data]
            rows = []
            for item in items:
                rows.append([
                    self._pick(item, "haste", "hastePercent", "percent", "value"),
                    self._pick(item, "frame", "uNowFrame", "nowFrame"),
                    self._pick(item, "time", "duration", "actual"),
                ])
            title = f"急速计算 CD {cooldown}"
            self._set_table(return_data, title, ["急速", "帧数", "实际时长"], rows, empty_msg="暂无急速数据")

        return await self._request_api("/skill/calculate", {"cooldown": cooldown, "token": self.token}, processor, "data_list.html")

    async def shilianmiaoshang(self, season: str, floor: int) -> Dict[str, Any]:
        """试炼秒伤"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            rows = []
            for item in items:
                rows.append([
                    self._pick(item, "name", "boss", "bossName"),
                    self._pick(item, "hp", "blood", "life"),
                    self._pick(item, "perfect", "dps180", "mainPerfect"),
                    self._pick(item, "pass", "dps300", "mainPass"),
                    self._pick(item, "shortPerfect", "dps120"),
                    self._pick(item, "shortPass", "dps180short"),
                ])
            title = f"{season} 第{floor}层秒伤"
            self._set_table(return_data, title, ["首领", "血量", "完美秒伤", "通关秒伤", "短时完美", "短时通关"], rows, empty_msg="暂无秒伤数据")

        return await self._request_api("/trial/bosses", {"season": season, "floor": floor, "token": self.token}, processor, "data_list.html")

    async def shiliansaiji(self) -> Dict[str, Any]:
        """试炼赛季"""
        async def processor(data: Any, return_data: Dict[str, Any]) -> None:
            items = self._as_list(data)
            rows = []
            for item in items:
                bosses = item.get("bosses") or item.get("list") or item.get("order") or []
                if isinstance(bosses, list):
                    boss_text = " / ".join(str(x.get("name") if isinstance(x, dict) else x) for x in bosses)
                else:
                    boss_text = str(bosses)
                rows.append([
                    self._pick(item, "name", "season", "title"),
                    self._pick(item, "start", "begin", "date"),
                    boss_text,
                ])
            self._set_table(return_data, "试炼赛季", ["赛季", "时间", "首领顺序"], rows, empty_msg="暂无赛季数据")

        return await self._request_api("/trial/seasons", {"token": self.token}, processor, "data_list.html")

    async def token_stats(self, token: str) -> dict:

        """查询令牌用量。POST /token/stats"""
        result = self._init_return_data()
        token = (token or "").strip()
        if not token:
            result["msg"] = "未提供 Token"
            return result
        data = await self._api.post("https://www.jx3api.com/token/stats", data={"token": token}, out_key=None)
        if not data:
            result["msg"] = "令牌无效或查询失败"
            return result
        payload = data.get("data") if isinstance(data, dict) and "data" in data else data
        if not isinstance(payload, dict):
            result["msg"] = "令牌无效或查询失败"
            return result
        level = payload.get("level")
        used = payload.get("used")
        remaining = payload.get("remaining")
        expire_at = payload.get("expireAt")
        valid = payload.get("valid")
        lines = ["JX3API 令牌状态"]
        if valid is not None:
            lines.append("状态：" + ("有效" if valid else "已失效"))
        if level is not None:
            lines.append(f"等级：LV.{level}")
        if used is not None:
            lines.append(f"已用：{used} 次")
        if str(level) == "2" or remaining is not None:
            if remaining is not None:
                lines.append(f"剩余：{remaining} 次")
        if expire_at:
            from datetime import datetime
            try:
                ts = int(expire_at)
                if ts > 10_000_000_000:
                    ts //= 1000
                lines.append("到期：" + datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"))
            except Exception:
                lines.append(f"到期：{expire_at}")
        elif str(level) == "1":
            lines.append("到期：永久")
        result["code"] = 200
        result["data"] = "\n".join(lines)
        return result
