from __future__ import annotations

import re

from typing import Any

from astrbot.api import logger

from .page_payload import read_json_payload
from .session_policy import is_group_umo

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
            ("/page/sessions/token", self.set_token, ["POST"], "设置会话 Token"),
            ("/page/sessions/ticket", self.set_ticket, ["POST"], "设置会话推栏"),
            ("/page/sessions/use-global", self.set_use_global, ["POST"], "设置是否使用全局 Token"),
            ("/page/sessions/clear-secret", self.clear_secret, ["POST"], "清除会话密钥"),
            ("/page/sessions/bot", self.set_bot, ["POST"], "设置会话是否启用机器人"),
            ("/page/sessions/claim", self.clear_claim, ["POST"], "取消认领资格"),
            ("/page/sessions/managers", self.save_managers, ["POST"], "保存会话授权管理"),
            ("/page/sessions/delete", self.delete_session, ["POST"], "删除群聊会话"),
            ("/page/commands", self.list_commands, ["GET"], "列出全局命令"),
            ("/page/commands/save", self.save_command, ["POST"], "保存全局命令"),
            ("/page/commands/reset", self.reset_commands, ["POST"], "恢复默认命令"),
            ("/page/push-commands", self.list_push_commands, ["GET"], "列出主动推送命令"),
            ("/page/push-commands/save", self.save_push_name, ["POST"], "保存推送事件名"),
            ("/page/push-commands/reset", self.reset_push_names, ["POST"], "恢复默认推送事件名"),
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
        sessions = []
        for row in rows:
            item = self.plugin.sessions.public_row(
                row,
                has_global_ticket=has_global_ticket,
                has_global_token=has_global_token,
                global_token=self.plugin._global_token(),
                global_ticket=self.plugin._global_ticket(),
            )
            item["managers"] = [
                {
                    "id": str(manager.get("user_id") or ""),
                    "name": str(manager.get("name") or manager.get("user_id") or ""),
                }
                for manager in await self.plugin.sessions.list_managers(row.get("umo") or "")
            ]
            sessions.append(item)
        return self.json_response({
            "sessions": sessions,
            "has_global_token": has_global_token,
            "has_global_ticket": has_global_ticket,
            "notice": "本页面只展示群聊会话，仅供 AstrBot 后台主人使用。",
        })

    async def _payload(self) -> dict[str, Any]:
        return await read_json_payload(self.request)

    async def bind_session(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        server = str(data.get("server") or "").strip()
        if not umo or not server:
            return self.error_response("缺少 umo 或区服", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
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
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        await self.plugin.sessions.clear_server(umo)
        await self.plugin.jx3at.refresh_jobs()
        return self.json_response({"ok": True})

    async def set_token(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        token = str(data.get("token") or "").strip()
        if not umo or not token:
            return self.error_response("缺少 umo 或 Token", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        values = [part.strip() for part in token.replace("，", ",").split(",") if part.strip()]
        if not values:
            return self.error_response("Token 不能为空", status_code=400)
        for index, value in enumerate(values, 1):
            result = await self.plugin.jx3api.token_stats(value)
            if result.get("code") != 200 or result.get("valid") is False:
                detail = str(result.get("msg") or "Token 不可用")
                message = self.plugin.jx3api._token_error_message(detail)
                return self.error_response(
                    f"第 {index} 个 Token 校验失败：{message}",
                    status_code=400,
                )
        await self.plugin.sessions.set_token(umo, token)
        return self.json_response({"ok": True})

    async def set_ticket(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        ticket = str(data.get("ticket") or "").strip()
        if not umo or not ticket:
            return self.error_response("缺少 umo 或推栏标识", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        values = [part.strip() for part in ticket.replace("，", ",").split(",") if part.strip()]
        if not values:
            return self.error_response("推栏标识不能为空", status_code=400)
        row = await self.plugin.sessions.get(umo)
        from .session_policy import CREDENTIAL_MISSING
        probe_token = self.plugin.sessions.resolve_token(row or {}, self.plugin._global_token())
        if probe_token == CREDENTIAL_MISSING:
            probe_token = ""
        elif "," in probe_token:
            probe_token = probe_token.split(",", 1)[0].strip()
        for index, value in enumerate(values, 1):
            ok, msg = await self.plugin.jx3api.validate_ticket(value, probe_token)
            if not ok:
                return self.error_response(
                    f"第 {index} 个推栏标识校验失败：{msg}",
                    status_code=400,
                )
        await self.plugin.sessions.set_ticket(umo, ticket)
        return self.json_response({"ok": True})

    async def set_use_global(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        enabled = bool(data.get("enabled"))
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
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
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        await self.plugin.sessions.clear_secret(umo, kind)
        return self.json_response({"ok": True})

    async def set_bot(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        enabled = bool(data.get("enabled"))
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        await self.plugin.sessions.set_bot_enabled(umo, enabled)
        return self.json_response({"ok": True})

    async def delete_session(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("只能删除群聊会话", status_code=400)
        deleted = await self.plugin.sessions.delete_session(umo)
        if not deleted:
            return self.error_response("未找到该会话", status_code=404)
        left, leave_detail = False, ""
        try:
            from .session_lifecycle import leave_group
            left, leave_detail = await leave_group(self.plugin.context, umo)
        except Exception:
            left, leave_detail = False, "退群动作执行异常"
        await self.plugin.jx3at.refresh_jobs()
        return self.json_response({
            "ok": True,
            "left": left,
            "leave_detail": leave_detail,
            "message": "已删除并退群" if left else "已删除会话；自动退群未执行成功",
        })

    async def clear_claim(self):
        data = await self._payload()
        identity = str(data.get("identity") or "").strip()
        if not identity:
            return self.error_response("缺少认领人身份", status_code=400)
        await self.plugin.sessions.clear_claimant(identity)
        return self.json_response({"ok": True})

    async def save_managers(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        managers_text = str(data.get("managers") or "").strip()
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        row = await self.plugin.sessions.get(umo)
        if not row:
            return self.error_response("未找到该会话", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        values = [
            part.strip().lstrip("@")
            for part in managers_text.replace("，", ",").split(",")
            if part.strip()
        ]
        seen = []
        for value in values:
            if value not in seen:
                seen.append(value)
        parsed = []
        for value in seen:
            match = re.fullmatch(r"(.+?)[（(]([^（）()]+)[）)]", value)
            parsed.append(match.group(2).strip() if match else value)
        ok, msg = await self.plugin.sessions.replace_managers(umo, parsed)
        if not ok:
            return self.error_response(msg, status_code=400)
        return self.json_response({"ok": True, "message": msg})

    async def list_commands(self):
        from .command_catalog import public_command_rows
        rows = [
            row for row in public_command_rows(self.plugin.command_catalog)
            if row["id"] not in {"打开", "关闭"}
        ]
        return self.json_response({
            "commands": rows,
            "notice": "命令修改全局生效。改名后只认新命令，不再认旧命令。",
        })

    async def save_command(self):
        from .command_catalog import apply_command_overrides, set_command_name
        data = await self._payload()
        command_id = str(data.get("id") or "").strip()
        name = str(data.get("command") or "").strip()
        _, error = set_command_name(self.plugin.command_catalog, command_id, name)
        if error:
            return self.error_response(error, status_code=400)
        overrides = await self.plugin.settings.command_overrides()
        if name == command_id:
            overrides.pop(command_id, None)
        else:
            overrides[command_id] = name
        await self.plugin.settings.set_command_overrides(overrides)
        self.plugin.command_catalog = apply_command_overrides(overrides)
        self.plugin.jx3api.command_catalog = self.plugin.command_catalog
        return self.json_response({"ok": True})

    async def reset_commands(self):
        from .command_catalog import apply_command_overrides
        await self.plugin.settings.set_command_overrides({})
        self.plugin.command_catalog = apply_command_overrides({})
        self.plugin.jx3api.command_catalog = self.plugin.command_catalog
        return self.json_response({"ok": True})

    async def list_push_commands(self):
        from .event_catalog import EVENT_DESCRIPTIONS, EVENT_GROUPS, normalize_push_overrides
        overrides = normalize_push_overrides(getattr(self.plugin, "push_name_overrides", {}) or {})
        open_name = str((self.plugin.command_catalog.get("打开") or {}).get("command") or "打开")
        close_name = str((self.plugin.command_catalog.get("关闭") or {}).get("command") or "关闭")

        def command_row(command_id: str) -> dict[str, str]:
            name = open_name if command_id == "打开" else close_name
            return {
                "id": command_id,
                "command": name,
                "example": f"{name} 事件类型",
            }

        groups = []
        for group in EVENT_GROUPS:
            events = []
            for item in group["items"]:
                events.append({
                    "action": str(item["action"]),
                    "kind": item["kind"],
                    "name": overrides.get(str(item["action"]), item["name"]),
                    "default": item["name"],
                    "desc": EVENT_DESCRIPTIONS.get(item["action"], item["kind"]),
                })
            groups.append({"name": group["name"], "events": events})
        return self.json_response({
            "open": command_row("打开"),
            "close": command_row("关闭"),
            "groups": groups,
            "notice": "主动推送命令与事件名修改后全局生效，只认新名称。",
        })

    async def save_push_name(self):
        from .event_catalog import (
            effective_push_items,
            has_duplicate_push_names,
            normalize_push_overrides,
        )
        data = await self._payload()
        action = str(data.get("action") or "").strip()
        name = str(data.get("name") or "").strip()
        if not action or not name:
            return self.error_response("缺少事件或名称", status_code=400)
        valid = {str(item["action"]) for item in effective_push_items()}
        if action not in valid:
            return self.error_response("未找到该事件", status_code=400)
        overrides = normalize_push_overrides(getattr(self.plugin, "push_name_overrides", {}) or {})
        default_names = {str(item["action"]): str(item["name"]) for item in effective_push_items()}
        if name == default_names.get(action, ""):
            overrides.pop(action, None)
        else:
            overrides[action] = name
        if has_duplicate_push_names(overrides):
            return self.error_response("该事件名与其他事件重名，请更换。", status_code=400)
        await self.plugin.settings.set_push_names(overrides)
        self.plugin.push_name_overrides = dict(overrides)
        self.plugin.jx3api.push_names = dict(overrides)
        return self.json_response({"ok": True})

    async def reset_push_names(self):
        await self.plugin.settings.set_push_names({})
        self.plugin.push_name_overrides = {}
        self.plugin.jx3api.push_names = {}
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

