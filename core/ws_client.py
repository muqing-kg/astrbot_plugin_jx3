from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable
from urllib.parse import quote

import aiohttp

from astrbot.api import logger

DEFAULT_WS_URL = "wss://socket.nicemoe.cn"


class JX3WSClient:
    """JX3API 事件通道。有订阅才连接，断线自动重连。"""

    def __init__(
        self,
        url: str = DEFAULT_WS_URL,
        token: str = "",
        on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        reconnect_interval: int = 5,
    ):
        self.url = (url or DEFAULT_WS_URL).rstrip("/")
        self.token = token or ""
        self.on_message = on_message
        self.reconnect_interval = reconnect_interval
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._wanted = False

    def set_token(self, token: str) -> None:
        self.token = token or ""

    async def set_wanted(self, wanted: bool) -> None:
        wanted = bool(wanted)
        if wanted == self._wanted:
            return
        self._wanted = wanted
        if wanted:
            await self.start()
        else:
            await self.stop()

    async def configure(self, token: str, wanted: bool) -> None:
        token = token or ""
        wanted = bool(wanted)
        token_changed = token != self.token
        self.token = token
        if wanted and (not self._wanted or token_changed):
            if self._wanted:
                await self.stop()
            await self.start()
            return
        if not wanted and self._wanted:
            await self.stop()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._wanted = True
        self._task = asyncio.create_task(self._run(), name="jx3-ws")

    async def stop(self) -> None:
        self._wanted = False
        self._stop.set()
        task = self._task
        self._task = None
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def _ws_url(self) -> str:
        if self.token:
            return f"{self.url}?token={quote(self.token, safe='')}"
        return self.url

    async def _run(self) -> None:
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=None)
        while self._wanted and not self._stop.is_set():
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.ws_connect(self._ws_url(), heartbeat=20) as ws:
                        logger.info("JX3API 事件通道已连接")
                        async for msg in ws:
                            if self._stop.is_set() or not self._wanted:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    payload = json.loads(msg.data)
                                except Exception:
                                    logger.warning("事件通道收到无法解析的消息")
                                    continue
                                if self.on_message:
                                    try:
                                        await self.on_message(payload)
                                    except Exception:
                                        logger.exception("事件通道处理消息失败")
                            elif msg.type in {aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                                break
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"JX3API 事件通道断开: {type(e).__name__}")
            if self._wanted and not self._stop.is_set():
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.reconnect_interval)
                except asyncio.TimeoutError:
                    pass
        logger.info("JX3API 事件通道已停止")
