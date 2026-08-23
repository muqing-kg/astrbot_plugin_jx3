from __future__ import annotations

from typing import Any

from astrbot.api import logger

PLUGIN_NAME = "astrbot_plugin_jx3"


class SessionPageAPI:
    def __init__(self, plugin: Any) -> None:
        self.plugin = plugin

    def register(self) -> None:
        try:
            from astrbot.api.web import error_response, json_response, request
        except Exception as e:
            logger.warning(f"当前 AstrBot 不支持插件页面 API: {e}")
            return
        self.json_response = json_response
        self.error_response = error_response
        self.request = request
        routes = [
            ("/page/sessions", self.list_sessions, ["GET"], "列出会话绑定"),
            ("/page/sessions/bind", self.bind_session, ["POST"], "绑定会话区服"),
            ("/page/sessions/push", self.set_push, ["POST"], "设置会话推送"),
            ("/page/sessions/token", self.set_token, ["POST"], "设置会话 Token"),
            ("/page/sessions/ticket", self.set_ticket, ["POST"], "设置会话推栏"),
            ("/page/sessions/use-global", self.set_use_global, ["POST"], "设置是否使用全局 Token"),
            ("/page/sessions/clear-secret", self.clear_secret, ["POST"], "清除会话密钥"),
        ]
        for route, handler, methods, description in routes:
            self.plugin.context.register_web_api(
                f"/{PLUGIN_NAME}{route}",
                handler,
                methods,
                description,
            )

    async def list_sessions(self):
        rows = await self.plugin.sessions.list_all()
        return self.json_response({
            "sessions": [self.plugin.sessions.public_row(row) for row in rows],
            "has_global_token": bool(self.plugin._global_token()),
            "has_global_ticket": bool(self.plugin._global_ticket()),
            "notice": "该页面仅供 AstrBot 后台主人使用，请勿暴露到公网。",
        })

    async def _payload(self) -> dict[str, Any]:
        try:
            data = await self.request.json
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    async def bind_session(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        server = str(data.get("server") or "").strip()
        if not umo or not server:
            return self.error_response("缺少 umo 或区服", status_code=400)
        await self.plugin.sessions.bind_server(umo, server)
        return self.json_response({"ok": True})

    async def set_push(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        kind = str(data.get("kind") or "").strip()
        enabled = bool(data.get("enabled"))
        ok, msg = await self.plugin.sessions.set_push(umo, kind, enabled)
        if not ok:
            return self.error_response(msg or "设置失败", status_code=400)
        await self.plugin.jx3at.refresh_jobs()
        return self.json_response({"ok": True})

    async def set_token(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        token = str(data.get("token") or "").strip()
        if not umo or not token:
            return self.error_response("缺少 umo 或 Token", status_code=400)
        await self.plugin.sessions.set_token(umo, token)
        return self.json_response({"ok": True})

    async def set_ticket(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        ticket = str(data.get("ticket") or "").strip()
        if not umo or not ticket:
            return self.error_response("缺少 umo 或推栏标识", status_code=400)
        await self.plugin.sessions.set_ticket(umo, ticket)
        return self.json_response({"ok": True})

    async def set_use_global(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        enabled = bool(data.get("enabled"))
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        await self.plugin.sessions.set_use_global_token(umo, enabled)
        return self.json_response({"ok": True})

    async def clear_secret(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        kind = str(data.get("kind") or "token").strip()
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        await self.plugin.sessions.clear_secret(umo, kind)
        return self.json_response({"ok": True})
