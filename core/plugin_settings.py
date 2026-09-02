from __future__ import annotations

import json
from urllib.parse import urlsplit, urlunsplit

from .sqlite import AsyncSQLiteDB


class PluginSettings:
    def __init__(self, sqlite: AsyncSQLiteDB):
        self.sql = sqlite

    COMMAND_ID_MIGRATIONS = {
        "拍卖": "阵营拍卖",
        "的卢": "的卢拍卖",
        "武林争霸": "武林争霸赛",
        "试炼之地": "试炼之地排行",
    }

    async def init(self) -> None:
        await self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_settings (
                key TEXT PRIMARY KEY,
                value TEXT DEFAULT ''
            )
            """
        )
        await self.sql.execute("DELETE FROM plugin_settings WHERE key='command_descs'")

    async def _get(self, key: str) -> str:
        row = await self.sql.select_one("plugin_settings", "key=?", (key,))
        return "" if not row else str(row.get("value") or "")

    async def _set(self, key: str, value: str) -> None:
        row = await self.sql.select_one("plugin_settings", "key=?", (key,))
        if row:
            await self.sql.update("plugin_settings", {"value": value}, "key=?", (key,))
            return
        await self.sql.insert("plugin_settings", {"key": key, "value": value})

    async def command_overrides(self) -> dict[str, str]:
        raw = await self._get("command_overrides")
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        overrides = {str(k): str(v) for k, v in data.items() if str(k) and str(v)}
        migrated = False
        for old_id, new_id in self.COMMAND_ID_MIGRATIONS.items():
            if old_id not in overrides:
                continue
            value = overrides.pop(old_id)
            migrated = True
            if value not in {old_id, new_id}:
                overrides.setdefault(new_id, value)
        if migrated:
            await self.set_command_overrides(overrides)
        return overrides

    async def server_aliases(self) -> dict[str, str]:
        raw = await self._get("server_aliases")
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        out = {}
        for key, value in data.items():
            if isinstance(value, list):
                out[str(key)] = "，".join(str(item) for item in value if str(item).strip())
            else:
                out[str(key)] = str(value)
        return out

    async def set_server_aliases(self, aliases: dict[str, str]) -> None:
        await self._set("server_aliases", json.dumps(aliases, ensure_ascii=False))

    async def push_name_overrides(self) -> dict[str, str]:
        raw = await self._get("push_name_overrides")
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        out = {}
        for key, value in data.items():
            action = str(key).strip()
            name = str(value or "").strip()
            if action and name:
                out[action] = name
        return out

    async def set_push_names(self, overrides: dict[str, str]) -> None:
        await self._set("push_name_overrides", json.dumps(overrides, ensure_ascii=False))

    async def set_command_overrides(self, overrides: dict[str, str]) -> None:
        await self._set("command_overrides", json.dumps(overrides, ensure_ascii=False))

    async def global_config(self, fallback: dict) -> dict[str, object]:
        stored_base = await self._get("jx3api_base_url")
        stored_ws = await self._get("jx3api_ws_url")
        stored_ssl = await self._get("jx3api_ssl_verify")
        stored_prefix_enable = await self._get("prefix_enable")
        stored_prefix_text = await self._get("prefix_text")
        return {
            "jx3api_base_url": stored_base or str(
                fallback.get("jx3api_base_url") or "https://www.jx3api.com"
            ),
            "jx3api_ws_url": stored_ws or str(
                fallback.get("jx3api_ws_url") or "wss://socket.nicemoe.cn"
            ),
            "jx3api_ssl_verify": (
                stored_ssl == "1" if stored_ssl else bool(fallback.get("jx3api_ssl_verify", True))
            ),
            "prefix_enable": (
                stored_prefix_enable == "1" if stored_prefix_enable else bool(
                    (fallback.get("prefix") or {}).get("enable", False)
                )
            ),
            "prefix_text": stored_prefix_text or str(
                (fallback.get("prefix") or {}).get("text") or "剑三"
            ),
        }

    async def set_global_config(self, values: dict[str, object]) -> None:
        await self._set("jx3api_base_url", str(values.get("jx3api_base_url") or ""))
        await self._set("jx3api_ws_url", str(values.get("jx3api_ws_url") or ""))
        await self._set(
            "jx3api_ssl_verify",
            "1" if values.get("jx3api_ssl_verify") else "0",
        )
        await self._set(
            "prefix_enable",
            "1" if values.get("prefix_enable") else "0",
        )
        await self._set("prefix_text", str(values.get("prefix_text") or ""))


def normalize_base_url(value: object) -> str:
    text = str(value or "").strip().rstrip("/")
    if not text:
        return "https://www.jx3api.com"
    parts = urlsplit(text)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("基础地址必须以 http:// 或 https:// 开头。")
    if parts.query or parts.fragment:
        raise ValueError("基础地址不能携带查询参数或锚点。")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
