# core/request.py
from contextlib import contextmanager
from contextvars import ContextVar
import json
import aiohttp
import asyncio
from typing import Any, Dict, Optional
from aiohttp import ClientTimeout, ClientSession

from .plugin_log import logger

_quiet_debug = ContextVar("jx3_quiet_request_debug", default=False)


@contextmanager
def quiet_request_debug():
    """Hide routine request DEBUG lines for a caller; errors stay visible."""
    token = _quiet_debug.set(True)
    try:
        yield
    finally:
        _quiet_debug.reset(token)

class APIClient:
    """
    API客户端类
    
    优化说明：
    1. 复用 aiohttp.ClientSession 以提高性能。
    2. 增加类型提示 (Type Hints)。
    3. 支持异步上下文管理器 (Async Context Manager)。
    """

    _SUCCESS_CODES = frozenset((200, "200", "0", 0, 1))

    def __init__(self, base_timeout: int = 10, ssl_verify: bool = True):
        self.base_timeout = base_timeout
        self.ssl_verify = ssl_verify
        self._session: Optional[ClientSession] = None

    async def get_session(self) -> ClientSession:
        """获取或创建单例 Session"""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self.base_timeout)
            self._session = ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """关闭 Session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        await self.get_session()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        await self.close()

    def _redact(self, data: Optional[Dict], keys=("token", "ticket")):
        if not data:
            return data
        hidden = dict(data)
        for key in keys:
            if hidden.get(key):
                hidden[key] = "***"
        return hidden

    async def _request(self, method: str, url: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Any:
        """
        统一的内部请求处理方法
        """
        session = await self.get_session()
        method = method.upper()
        
        # 记录日志
        if not _quiet_debug.get():
            logger.debug(f"发起 {method} 请求: {url}")
            if params: logger.debug(f"Query参数: {self._redact(params)}")
            if json_data: logger.debug(f"Body数据: {self._redact(json_data)}")

        try:
            # aiohttp 会自动处理 json=json_data 时的 Content-Type
            async with session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                ssl=self.ssl_verify
            ) as response:
                return await self._handle_response(response)
                
        except aiohttp.ClientError as e:
            logger.error(f"网络请求出错 ({method} {url}): {e}")
            return None
        except Exception as e:
            logger.error(f"未知错误 ({method} {url}): {e}")
            return None

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """处理响应：自动识别二进制或JSON"""
        try:
            if not _quiet_debug.get():
                logger.debug(f"响应状态: {response.status}")
            if response.status in (401, 403):
                try:
                    detail = (await response.text()).strip()
                except Exception:
                    detail = ""
                return {
                    "_error": detail or f"HTTP {response.status}",
                    "_code": response.status,
                }
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').lower()

            if 'image' in content_type or 'octet-stream' in content_type:
                return await response.read()

            try:
                data = await response.json()
            except Exception:
                text = await response.text()
                try:
                    loop = asyncio.get_running_loop()
                    data = await loop.run_in_executor(None, json.loads, text)
                except json.JSONDecodeError:
                    logger.error(f"无法解析响应为 JSON。原始内容: {text[:100]}...")
                    return None

            if not _quiet_debug.get():
                logger.debug(f"响应数据: {type(data).__name__}, 长度 {len(data) if hasattr(data, '__len__') else '未知'}")
            return self._validate_api_payload(data)

        except aiohttp.ClientError as e:
            logger.error(f"HTTP响应错误: {e}")
            return None

    def _validate_api_payload(self, data: Any) -> Any:
        """校验业务层面的 JSON 数据结构"""
        if not data:
            logger.error("API返回空数据")
            return None

        # 如果返回的是 JSON 字符串而非对象，再次解析
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return None
        
        if isinstance(data, dict) and 'code' in data:
            code = data.get('code')
            # 按 JX3API 当前接口文档维护成功码白名单，上游新增成功码时需同步。
            if code not in self._SUCCESS_CODES:
                msg = data.get('msg') or data.get('message', '未知错误')
                logger.error(f"API业务报错: code={code}, msg={msg}")
                return {"_error": str(msg), "_code": code}
        
        return data

    async def get(self, url: str, params: Optional[Dict] = None, out_key: Optional[str] = None) -> Any:
        """GET 请求封装"""
        data = await self._request('GET', url, params=params)
        return self._extract_data(data, out_key)

    async def post(self, url: str, data: Optional[Dict] = None, out_key: Optional[str] = None) -> Any:
        """POST 请求封装 (默认发送 JSON)"""
        data = await self._request('POST', url, json_data=data)
        return self._extract_data(data, out_key)

    def _extract_data(self, data: Any, key: Optional[str]) -> Any:
        """辅助方法：从结果中提取指定字段"""
        if data is None:
            return None
        if isinstance(data, bytes):
            return data
        if isinstance(data, dict) and data.get("_error"):
            return data
        if key and isinstance(data, dict):
            return data.get(key, {})
        return data
