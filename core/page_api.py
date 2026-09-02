from __future__ import annotations

import re

from typing import Any

from astrbot.api import logger

from .group_info import refresh_missing_group_display_names
from .page_payload import read_json_payload
from .session_policy import is_group_umo, mask_for_user

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
            ("/page/global-config", self.list_global_config, ["GET"], "列出全局配置"),
            ("/page/global-config/save", self.save_global_config, ["POST"], "保存全局配置"),
            ("/page/credentials", self.list_global_credentials, ["GET"], "列出全局凭据"),
            ("/page/credentials/add", self.add_global_credential, ["POST"], "添加全局凭据"),
            ("/page/credentials/delete", self.delete_global_credential, ["POST"], "删除全局凭据"),
            ("/page/sessions/bind", self.bind_session, ["POST"], "绑定会话区服"),
            ("/page/sessions/clear-server", self.clear_server, ["POST"], "清除会话区服"),
            ("/page/sessions/token", self.set_token, ["POST"], "设置会话接口令牌"),
            ("/page/sessions/push-token", self.set_push_token, ["POST"], "设置会话推送令牌"),
            ("/page/sessions/ticket", self.set_ticket, ["POST"], "设置会话推栏"),
            ("/page/sessions/use-global", self.set_use_global, ["POST"], "设置是否使用全局凭据"),
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
        await self.plugin.sessions.mark_astrbot_admin_claims(self.plugin._astrbot_admin_ids())
        rows = await self.plugin.sessions.list_bound()
        rows = await refresh_missing_group_display_names(self.plugin.context, self.plugin.sessions, rows)
        umos = [str(row.get("umo") or "") for row in rows]
        credential_rows = await self.plugin.sessions.list_credentials_for_umos(umos)
        credentials_by: dict[tuple[str, str], list[dict]] = {}
        for row_data in credential_rows:
            key = (str(row_data.get("umo") or ""), str(row_data.get("kind") or ""))
            credentials_by.setdefault(key, []).append(row_data)
        manager_rows = await self.plugin.sessions.list_managers_for_umos(umos)
        global_values = {
            kind: await self.plugin.sessions.list_active_global_credentials(kind)
            for kind in ("token", "push_token", "ticket")
        }
        sessions = []
        for row in rows:
            item = self.plugin.sessions.public_row(row)
            umo = str(row.get("umo") or "")
            for kind in ("token", "push_token", "ticket"):
                records = credentials_by.get((umo, kind), [])
                source, _values = self.plugin.sessions.resolve_credential_pool_for_records(
                    row, records, global_values[kind], kind
                )
                active = [item for item in records if item.get("status") == "active"]
                removed = [item for item in records if item.get("status") == "removed"]
                plural = "token" if kind == "token" else kind
                item[f"{plural}s"] = active
                item[f"removed_{plural}s"] = removed
                item[f"use_global_{kind}"] = bool(row.get(f"use_global_{kind}"))
                item.update(self._pool_status(kind, source, active, removed))
            item["managers"] = [
                {
                    "id": str(manager.get("user_id") or ""),
                    "name": str(manager.get("name") or manager.get("user_id") or ""),
                }
                for manager in manager_rows.get(umo, [])
            ]
            sessions.append(item)
        return self.json_response({
            "sessions": sessions,
            "notice": "本页面只展示群聊会话，仅供 AstrBot 后台主人使用。",
        })

    @staticmethod
    def _pool_status(
        kind: str,
        source: str,
        active: list[dict],
        removed: list[dict],
    ) -> dict[str, object]:
        labels = {
            "token": "接口令牌",
            "push_token": "推送令牌",
            "ticket": "推栏标识",
        }
        label = labels[kind]
        if source.startswith("group"):
            status = f"{len(active)} 枚群属{label}" if active else "群属失效池"
            source_name = "group" if active else "none"
        elif source.startswith("global") and source != "global_missing":
            status = "已配置全局"
            source_name = "global"
        elif source == "global_missing":
            status = "全局未配置"
            source_name = "none"
        else:
            status = "未配置"
            source_name = "none"
        return {
            f"{kind}_source": source_name,
            f"{kind}_status": status,
            f"has_{kind}": bool(active),
        }

    async def _payload(self) -> dict[str, Any]:
        return await read_json_payload(self.request)

    async def list_global_config(self):
        config = await self.plugin.settings.global_config(self.plugin.conf)
        return self.json_response({"config": config})

    async def save_global_config(self):
        from urllib.parse import urlsplit

        from .plugin_settings import normalize_base_url

        data = await self._payload()
        try:
            base_url = normalize_base_url(data.get("jx3api_base_url"))
        except ValueError as exc:
            return self.error_response(str(exc), status_code=400)
        ws_url = str(data.get("jx3api_ws_url") or "").strip().rstrip("/")
        ws_parts = urlsplit(ws_url)
        if ws_parts.scheme not in {"ws", "wss"} or not ws_parts.netloc:
            return self.error_response("事件通道地址必须以 ws:// 或 wss:// 开头。", status_code=400)
        prefix_text = str(data.get("prefix_text") or "").strip()
        prefix_enable = bool(data.get("prefix_enable"))
        if prefix_enable and not prefix_text:
            return self.error_response("启用插件前缀时必须填写前缀内容。", status_code=400)
        values = {
            "jx3api_base_url": base_url,
            "jx3api_ws_url": ws_url,
            "jx3api_ssl_verify": bool(data.get("jx3api_ssl_verify", True)),
            "prefix_enable": prefix_enable,
            "prefix_text": prefix_text or "剑三",
        }
        await self.plugin.settings.set_global_config(values)
        self.plugin.conf.update(values)
        self.plugin.prefix = {
            "enable": values["prefix_enable"],
            "text": values["prefix_text"],
        }
        self.plugin.jx3api._api.ssl_verify = values["jx3api_ssl_verify"]
        self.plugin.jx3box._api.ssl_verify = values["jx3api_ssl_verify"]
        self.plugin.aijx3._api.ssl_verify = values["jx3api_ssl_verify"]
        await self.plugin.jx3at.refresh_jobs()
        save = getattr(self.plugin.conf, "save_config_async", None)
        if callable(save):
            await save()
        return self.json_response({"ok": True, "config": values})

    async def list_global_credentials(self):
        tokens = await self.plugin.sessions.list_global_credentials("token", "active")
        removed_tokens = await self.plugin.sessions.list_global_credentials("token", "removed")
        push_tokens = await self.plugin.sessions.list_global_credentials("push_token", "active")
        removed_push_tokens = await self.plugin.sessions.list_global_credentials("push_token", "removed")
        tickets = await self.plugin.sessions.list_global_credentials("ticket")
        return self.json_response({
            "tokens": tokens,
            "push_tokens": push_tokens,
            "removed_tokens": removed_tokens,
            "removed_push_tokens": removed_push_tokens,
            "tickets": tickets,
        })

    async def add_global_credential(self):
        data = await self._payload()
        kind = str(data.get("kind") or "").strip()
        value = str(data.get("value") or "").strip()
        if kind not in {"token", "push_token", "ticket"}:
            return self.error_response("不支持的凭据类型", status_code=400)
        if not value:
            labels = {"token": "接口令牌", "push_token": "推送令牌", "ticket": "推栏标识"}
            label = labels[kind]
            return self.error_response(f"缺少全局{label}", status_code=400)
        if "," in value or "，" in value:
            return self.error_response("一次只能添加一条全局凭据。", status_code=400)
        existing = await self.plugin.sessions.get_global_credential(kind, value)
        if existing and existing.get("status") == "active":
            labels = {"token": "接口令牌", "push_token": "推送令牌", "ticket": "推栏标识"}
            label = labels[kind]
            return self.error_response(f"该全局{label}已在可用池中。", status_code=400)
        added = await self.plugin.sessions.add_global_credential(kind, value)
        if kind == "push_token":
            await self.plugin.jx3at.refresh_jobs()
        return self.json_response({"ok": True})

    async def delete_global_credential(self):
        data = await self._payload()
        try:
            credential_id = int(data.get("id") or 0)
        except (TypeError, ValueError):
            credential_id = 0
        if credential_id <= 0:
            return self.error_response("缺少凭据 ID", status_code=400)
        row = await self.plugin.sessions.sql.select_one("global_credentials", "id=?", (credential_id,))
        deleted = await self.plugin.sessions.delete_global_credential(credential_id)
        if not deleted:
            return self.error_response("未找到该全局凭据", status_code=404)
        if row and row.get("kind") == "push_token":
            await self.plugin.jx3at.refresh_jobs()
        return self.json_response({"ok": True})

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
            return self.error_response("缺少 umo 或接口令牌", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        if "," in token or "，" in token:
            return self.error_response("一次只能添加一条接口令牌。", status_code=400)
        from .credentials import validate_pool_token
        ok, message, remaining = await validate_pool_token(self.plugin.jx3api, token)
        if not ok:
            return self.error_response(f"接口令牌 {mask_for_user(token)} 校验失败：{message}", status_code=400)
        existing = await self.plugin.sessions.get_credential(umo, "token", token)
        if existing and existing.get("status") == "active":
            return self.error_response("该接口令牌已在可用池中。", status_code=400)
        added = await self.plugin.sessions.add_active_credential(umo, "token", token)
        if not added:
            return self.error_response("该接口令牌已在可用池中。", status_code=400)
        return self.json_response({"ok": True})

    async def set_push_token(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        token = str(data.get("token") or "").strip()
        if not umo or not token:
            return self.error_response("缺少 umo 或推送令牌", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        if "," in token or "，" in token:
            return self.error_response("一次只能添加一条推送令牌。", status_code=400)
        from .credentials import validate_pool_token

        ok, message, _remaining = await validate_pool_token(self.plugin.jx3api, token)
        if not ok:
            return self.error_response(f"推送令牌 {mask_for_user(token)} 校验失败：{message}", status_code=400)
        added = await self.plugin.sessions.add_active_credential(umo, "push_token", token)
        if not added:
            return self.error_response("该推送令牌已在可用池中。", status_code=400)
        await self.plugin.jx3at.refresh_jobs()
        return self.json_response({"ok": True})

    async def set_ticket(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        ticket = str(data.get("ticket") or "").strip()
        if not umo or not ticket:
            return self.error_response("缺少 umo 或推栏标识", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        if "," in ticket or "，" in ticket:
            return self.error_response("一次只能添加一条推栏标识。", status_code=400)
        _source, pool_values = await self.plugin.sessions.resolve_credential_pool(umo, "token")
        probe_token = pool_values[0] if pool_values else ""
        from .credentials import validate_pool_ticket
        ok, message, _ = await validate_pool_ticket(self.plugin.jx3api, ticket, probe_token)
        if not ok:
            return self.error_response(f"推栏标识 {mask_for_user(ticket)} 校验失败：{message}", status_code=400)
        existing = await self.plugin.sessions.get_credential(umo, "ticket", ticket)
        if existing and existing.get("status") == "active":
            return self.error_response("该推栏标识已在可用池中。", status_code=400)
        added = await self.plugin.sessions.add_active_credential(umo, "ticket", ticket)
        if not added:
            return self.error_response("该推栏标识已在可用池中。", status_code=400)
        return self.json_response({"ok": True})

    async def set_use_global(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        enabled = bool(data.get("enabled"))
        kind = str(data.get("kind") or "token").strip()
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        if kind not in {"token", "push_token", "ticket"}:
            return self.error_response("不支持的密钥类型", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        if enabled and await self.plugin.sessions.list_active_credentials(umo, kind):
            return self.error_response("群属可用池不为空，不能启用全局凭据。", status_code=400)
        await self.plugin.sessions.set_use_global_credential(umo, kind, enabled)
        if kind == "push_token":
            await self.plugin.jx3at.refresh_jobs()
        return self.json_response({"ok": True})

    async def clear_secret(self):
        data = await self._payload()
        umo = str(data.get("umo") or "").strip()
        kind = str(data.get("kind") or "token").strip()
        if not umo:
            return self.error_response("缺少 umo", status_code=400)
        if kind not in {"token", "push_token", "ticket"}:
            return self.error_response("不支持的密钥类型", status_code=400)
        if not is_group_umo(umo):
            return self.error_response("本插件只支持群聊会话", status_code=400)
        if kind in {"token", "push_token", "ticket"}:
            await self.plugin.sessions.sql.execute(
                "DELETE FROM session_credentials WHERE umo=? AND kind=? AND status='active'",
                (umo, kind),
            )
        if kind == "ticket":
            await self.plugin.sessions.set_use_global_credential(umo, kind, True)
        if kind == "push_token":
            await self.plugin.jx3at.refresh_jobs()
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

