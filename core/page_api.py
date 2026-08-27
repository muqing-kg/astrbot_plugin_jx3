from __future__ import annotations

from typing import Any

from astrbot.api import logger

from .page_payload import read_json_payload

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
            ("/page/sessions/clear-server", self.clear_server, ["POST"], "清除会话区服"),
            ("/page/sessions/push", self.set_push, ["POST"], "设置会话推送"),
            ("/page/sessions/token", self.set_token, ["POST"], "设置会话 Token"),
            ("/page/sessions/ticket", self.set_ticket, ["POST"], "设置会话推栏"),
            ("/page/sessions/use-global", self.set_use_global, ["POST"], "设置是否使用全局 Token"),
            ("/page/sessions/clear-secret", self.clear_secret, ["POST"], "清除会话密钥"),
            ("/page/sessions/bot", self.set_bot, ["POST"], "设置会话是否启用机器人"),
            ("/page/commands", self.list_commands, ["GET"], "列出全局命令"),
            ("/page/commands/save", self.save_command, ["POST"], "保存全局命令"),
            ("/page/commands/reset", self.reset_commands, ["POST"], "恢复默认命令"),
            ("/page/servers", self.list_servers, ["GET"], "列出区服别名"),
            ("/page/servers/save", self.save_server, ["POST"], "保存区服别名"),
            ("/page/servers/reset", self.reset_servers, ["POST"], "恢复默认区服别名"),
        ]
        for route, handler, methods, description in routes:
            self.plugin.context.register_web_api(
                f"/{PLUGIN_NAME}{route}",
                handler,
                methods,
                description,
            )

    async def list_sessions(self):
        rows = await self.plugin.sessions.list_bound()
        has_global_ticket = bool(self.plugin._global_ticket())
        has_global_token = bool(self.plugin._global_token())
        return self.json_response({
            "sessions": [
                self.plugin.sessions.public_row(
                    row,
                    has_global_ticket=has_global_ticket,
                    has_global_token=has_global_token,
                )
                for row in rows
            ],
            "has_global_token": has_global_token,
            "has_global_ticket": has_global_ticket,
            "notice": "该页面仅供 AstrBot 后台主人使用，请勿暴露到公网。",
        })

    async def _payload(self) -> dict[str, Any]:
        return await read_json_payload(self.request)

    async def bind_session(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        server = str(data.get("server") or "").strip()
        if not umo or not server:
            return self.error_response("缺少 umo 或区服", status_code=400)
        from .server_catalog import canonical_server
        official = canonical_server(self.plugin.server_catalog, server)
        if not official:
            return self.error_response("未识别的区服。请使用正式区服名或已配置的别名。", status_code=400)
        await self.plugin.sessions.bind_server(umo, official)
        return self.json_response({"ok": True, "server": official})

    async def clear_server(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        await self.plugin.sessions.clear_server(umo)
        await self.plugin.jx3at.refresh_jobs()
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
        if kind not in {"token", "ticket"}:
            return self.error_response("不支持的密钥类型", status_code=400)
        await self.plugin.sessions.clear_secret(umo, kind)
        return self.json_response({"ok": True})

    async def set_bot(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        enabled = bool(data.get("enabled"))
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        await self.plugin.sessions.set_bot_enabled(umo, enabled)
        return self.json_response({"ok": True})

    async def list_commands(self):
        from .command_catalog import public_command_rows
        return self.json_response({
            "commands": public_command_rows(self.plugin.command_catalog),
            "notice": "命令修改全局生效。改名后只认新命令，不再认旧命令。",
        })

    async def save_command(self):
        from .command_catalog import apply_command_overrides, set_command_name
        data = await self._payload()
        command_id = str(data.get("id") or "").strip()
        name = str(data.get("command") or "").strip()
        desc = str(data.get("desc") or "").strip()
        catalog, error = set_command_name(self.plugin.command_catalog, command_id, name)
        if error:
            return self.error_response(error, status_code=400)
        if desc:
            catalog[command_id]["desc"] = desc
        overrides = await self.plugin.settings.command_overrides()
        if name == command_id:
            overrides.pop(command_id, None)
        else:
            overrides[command_id] = name
        await self.plugin.settings.set_command_overrides(overrides)
        descs = await self.plugin.settings.command_descs()
        if desc:
            descs[command_id] = desc
        else:
            descs.pop(command_id, None)
        await self.plugin.settings.set_command_descs(descs)
        self.plugin.command_catalog = apply_command_overrides(overrides)
        for key, value in descs.items():
            if key in self.plugin.command_catalog and value:
                self.plugin.command_catalog[key]["desc"] = value
        self.plugin.jx3api.command_catalog = self.plugin.command_catalog
        return self.json_response({"ok": True})

    async def reset_commands(self):
        from .command_catalog import apply_command_overrides
        await self.plugin.settings.set_command_overrides({})
        await self.plugin.settings.set_command_descs({})
        self.plugin.command_catalog = apply_command_overrides({})
        self.plugin.jx3api.command_catalog = self.plugin.command_catalog
        return self.json_response({"ok": True})

    async def list_servers(self):
        from .server_catalog import public_server_rows
        return self.json_response({
            "servers": public_server_rows(self.plugin.server_catalog),
            "notice": "别名全局生效。查询和绑定可用别名，返回内容始终用正式区服名。",
        })

    async def save_server(self):
        from .server_catalog import apply_alias_overrides, set_server_aliases
        data = await self._payload()
        server = str(data.get("server") or "").strip()
        aliases = str(data.get("aliases") or "").strip()
        catalog, error = set_server_aliases(self.plugin.server_catalog, server, aliases)
        if error:
            return self.error_response(error, status_code=400)
        stored = await self.plugin.settings.server_aliases()
        stored[server] = aliases
        await self.plugin.settings.set_server_aliases(stored)
        self.plugin.server_catalog = apply_alias_overrides(stored)
        return self.json_response({"ok": True})

    async def reset_servers(self):
        from .server_catalog import apply_alias_overrides
        await self.plugin.settings.set_server_aliases({})
        self.plugin.server_catalog = apply_alias_overrides({})
        return self.json_response({"ok": True})

