from __future__ import annotations

import asyncio
import json
import inspect
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import aiohttp

from astrbot.api import logger

DEFAULT_WS_URL = "wss://socket.nicemoe.cn"
HEARTBEAT_INTERVAL = 30
RECONNECT_BASE_DELAY = 1
RECONNECT_MAX_DELAY = 30

SyncOrAsyncCallback = Callable[..., Any]


class JX3WSClient:
    """JX3API 事件通道。有订阅才连接，断线自动重连。"""

    def __init__(
        self,
        url: str = DEFAULT_WS_URL,
        token: str = "",
        on_message: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_open: SyncOrAsyncCallback | None = None,
        on_close: SyncOrAsyncCallback | None = None,
        on_error: SyncOrAsyncCallback | None = None,
        reconnect_base_seconds: float = RECONNECT_BASE_DELAY,
        reconnect_max_seconds: float = RECONNECT_MAX_DELAY,
    ):
        self.url = (url or DEFAULT_WS_URL).rstrip("/")
        self.token = token or ""
        self.on_message = on_message
        self.on_open = on_open
        self.on_close = on_close
        self.on_error = on_error
        self.reconnect_base_seconds = max(0.0, float(reconnect_base_seconds))
        self.reconnect_max_seconds = max(
            self.reconnect_base_seconds,
            float(reconnect_max_seconds),
        )
        self.reconnect_attempts = 0
        self._task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._wanted = False

    async def configure(self, token: str, wanted: bool, url: str | None = None) -> None:
        token = token or ""
        wanted = bool(wanted)
        token_changed = token != self.token
        url_changed = bool(url and url.rstrip("/") != self.url.rstrip("/"))
        if url:
            self.url = url.rstrip("/")
        self.token = token
        if wanted and (not self._wanted or token_changed or url_changed):
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
            parts = urlsplit(self.url)
            query = [
                (key, value)
                for key, value in parse_qsl(parts.query, keep_blank_values=True)
                if key != "token"
            ]
            query.append(("token", self.token))
            return urlunsplit((
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query),
                parts.fragment,
            ))
        return self.url

    async def _notify(self, callback: SyncOrAsyncCallback | None, *args: Any) -> None:
        if callback is None:
            return
        try:
            result = callback(*args)
            if inspect.isawaitable(result):
                await result
        except Exception:
            logger.exception("JX3API 事件通道回调执行失败")

    async def _heartbeat(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        try:
            while not self._stop.is_set() and not ws.closed:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if self._stop.is_set() or ws.closed:
                    break
                await ws.send_str(json.dumps({"action": -1}, separators=(",", ":")))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(f"JX3API 事件通道心跳发送失败: {type(exc).__name__}")
            await self._notify(self.on_error, exc)

    async def _run(self) -> None:
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=None)
        while self._wanted and not self._stop.is_set():
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    headers = {"token": self.token} if self.token else None
                    async with session.ws_connect(self._ws_url(), headers=headers, heartbeat=20) as ws:
                        logger.info("JX3API 事件通道已连接")
                        self.reconnect_attempts = 0
                        self._heartbeat_task = asyncio.create_task(
                            self._heartbeat(ws),
                            name="jx3-ws-heartbeat",
                        )
                        await self._notify(self.on_open)
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
                            elif msg.type in {
                                aiohttp.WSMsgType.CLOSE,
                                aiohttp.WSMsgType.CLOSED,
                                aiohttp.WSMsgType.ERROR,
                            }:
                                break
                        await self._notify(
                            self.on_close,
                            ws.close_code or aiohttp.WSCloseCode.ABNORMAL_CLOSURE,
                            str(getattr(ws, "close_reason", "") or ""),
                        )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"JX3API 事件通道断开: {type(e).__name__}")
                await self._notify(self.on_error, e)
            finally:
                if self._heartbeat_task:
                    self._heartbeat_task.cancel()
                    try:
                        await self._heartbeat_task
                    except asyncio.CancelledError:
                        pass
                    self._heartbeat_task = None
            if self._wanted and not self._stop.is_set():
                delay = min(
                    self.reconnect_base_seconds * (2 ** self.reconnect_attempts),
                    self.reconnect_max_seconds,
                )
                self.reconnect_attempts += 1
                logger.info(f"JX3API 事件通道将在 {delay:g} 秒后重连")
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass
        logger.info("JX3API 事件通道已停止")
