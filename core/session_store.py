from __future__ import annotations

from datetime import datetime
from typing import Any

from .event_catalog import GLOBAL_KINDS, PUSH_FIELD, PUSH_TYPES
from .session_policy import (
    CREDENTIAL_MISSING,
    NEED_TICKET,
    NEED_TOKEN,
    UNBOUND_SERVER,
    mask_secret,
    resolve_query_server,
)
from .sqlite import AsyncSQLiteDB

__all__ = [
    "CREDENTIAL_MISSING",
    "NEED_TICKET",
    "NEED_TOKEN",
    "PUSH_TYPES",
    "UNBOUND_SERVER",
    "SessionStore",
    "mask_secret",
    "resolve_query_server",
]


class SessionStore:
    def __init__(self, sqlite: AsyncSQLiteDB):
        self.sql = sqlite

    async def init(self) -> None:
        await self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS session_config (
                umo TEXT PRIMARY KEY,
                display_name TEXT DEFAULT '',
                server TEXT DEFAULT '',
                token TEXT DEFAULT '',
                ticket TEXT DEFAULT '',
                use_global_token INTEGER DEFAULT 0,
                push_kaifu INTEGER DEFAULT 0,
                push_xinwen INTEGER DEFAULT 0,
                push_shuma INTEGER DEFAULT 0,
                push_chitu INTEGER DEFAULT 0,
                push_gengxin INTEGER DEFAULT 0,
                push_bagua INTEGER DEFAULT 0,
                push_guanai INTEGER DEFAULT 0,
                push_yuncong INTEGER DEFAULT 0,
                push_qiyu INTEGER DEFAULT 0,
                push_fuyao INTEGER DEFAULT 0,
                push_dilu INTEGER DEFAULT 0,
                push_diaoluo INTEGER DEFAULT 0,
                push_paimai INTEGER DEFAULT 0,
                push_zhue INTEGER DEFAULT 0,
                push_zhuihun INTEGER DEFAULT 0,
                push_jisi INTEGER DEFAULT 0,
                push_xuanzhan INTEGER DEFAULT 0,
                push_judian INTEGER DEFAULT 0,
                push_weibo INTEGER DEFAULT 0,
                bot_enabled INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT ''
            )
            """
        )
        extra_columns = [
            "bot_enabled INTEGER DEFAULT 1",
            "push_gengxin INTEGER DEFAULT 0",
            "push_bagua INTEGER DEFAULT 0",
            "push_guanai INTEGER DEFAULT 0",
            "push_yuncong INTEGER DEFAULT 0",
            "push_qiyu INTEGER DEFAULT 0",
            "push_fuyao INTEGER DEFAULT 0",
            "push_dilu INTEGER DEFAULT 0",
            "push_diaoluo INTEGER DEFAULT 0",
            "push_paimai INTEGER DEFAULT 0",
            "push_zhue INTEGER DEFAULT 0",
            "push_zhuihun INTEGER DEFAULT 0",
            "push_jisi INTEGER DEFAULT 0",
            "push_xuanzhan INTEGER DEFAULT 0",
            "push_judian INTEGER DEFAULT 0",
            "push_weibo INTEGER DEFAULT 0",
        ]
        for column in extra_columns:
            try:
                await self.sql.execute(
                    f"ALTER TABLE session_config ADD COLUMN {column}"
                )
            except Exception:
                pass
        await self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_admin (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                user_id TEXT DEFAULT '',
                name TEXT DEFAULT '',
                claimed_at TEXT DEFAULT ''
            )
            """
        )
        await self.sql.execute(
            """
            INSERT OR IGNORE INTO plugin_admin (id, user_id, name, claimed_at)
            VALUES (1, '', '', '')
            """
        )
        await self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS push_state (
                kind TEXT NOT NULL,
                server TEXT NOT NULL,
                status TEXT DEFAULT '',
                PRIMARY KEY (kind, server)
            )
            """
        )

    async def ensure(self, umo: str, display_name: str = "") -> dict[str, Any]:
        row = await self.get(umo)
        if row:
            if display_name and row.get("display_name") != display_name:
                await self.sql.update(
                    "session_config",
                    {"display_name": display_name, "updated_at": _now()},
                    "umo=?",
                    (umo,),
                )
                row["display_name"] = display_name
            return row
        await self.sql.insert(
            "session_config",
            {
                "umo": umo,
                "display_name": display_name,
                "server": "",
                "token": "",
                "ticket": "",
                "use_global_token": 0,
                "push_kaifu": 0,
                "push_xinwen": 0,
                "push_shuma": 0,
                "push_chitu": 0,
                "bot_enabled": 1,
                "updated_at": _now(),
            },
        )
        return await self.get(umo)

    async def get(self, umo: str) -> dict[str, Any] | None:
        if not umo:
            return None
        return await self.sql.select_one("session_config", "umo=?", (umo,))

    async def list_all(self) -> list[dict[str, Any]]:
        return await self.sql.select_all("session_config")

    async def list_bound(self) -> list[dict[str, Any]]:
        rows = await self.list_all()
        return [row for row in rows if (row.get("server") or "").strip()]

    async def bind_server(self, umo: str, server: str, display_name: str = "") -> dict[str, Any]:
        await self.ensure(umo, display_name)
        resolver = getattr(self, "resolve_server", None)
        if callable(resolver):
            official = resolver(server)
            if official:
                server = official
        data = {"server": server.strip(), "updated_at": _now()}
        if display_name:
            data["display_name"] = display_name
        await self.sql.update("session_config", data, "umo=?", (umo,))
        return await self.get(umo)

    async def clear_server(self, umo: str) -> dict[str, Any]:
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {
                "server": "",
                **{field: 0 for field in PUSH_FIELD.values()},
                "updated_at": _now(),
            },
            "umo=?",
            (umo,),
        )
        return await self.get(umo)

    async def set_push(self, umo: str, kind: str, enabled: bool) -> tuple[bool, str]:
        if kind not in PUSH_FIELD:
            return False, "不支持的推送类型"
        row = await self.ensure(umo)
        if enabled and kind not in GLOBAL_KINDS and not (row.get("server") or "").strip():
            return False, "请先绑定区服后再打开推送。"
        await self.sql.update(
            "session_config",
            {PUSH_FIELD[kind]: 1 if enabled else 0, "updated_at": _now()},
            "umo=?",
            (umo,),
        )
        return True, ""

    async def set_token(self, umo: str, token: str) -> None:
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"token": token.strip(), "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def set_ticket(self, umo: str, ticket: str) -> None:
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"ticket": ticket.strip(), "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def set_bot_enabled(self, umo: str, enabled: bool) -> None:
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"bot_enabled": 1 if enabled else 0, "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    def is_bot_enabled(self, row: dict[str, Any] | None) -> bool:
        if not row:
            return True
        if "bot_enabled" not in row or row.get("bot_enabled") is None:
            return True
        return bool(row.get("bot_enabled"))

    async def set_use_global_token(self, umo: str, enabled: bool) -> None:
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"use_global_token": 1 if enabled else 0, "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def clear_secret(self, umo: str, kind: str) -> None:
        if kind not in ("token", "ticket"):
            raise ValueError(f"不支持的密钥类型: {kind}")
        field = "token" if kind == "token" else "ticket"
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {field: "", "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    def resolve_token(self, row: dict[str, Any] | None, global_token: str = "") -> str:
        if row:
            own = (row.get("token") or "").strip()
            if own:
                return own
            if row.get("use_global_token") and (global_token or "").strip():
                return global_token.strip()
        return CREDENTIAL_MISSING

    def resolve_ticket(self, row: dict[str, Any] | None, global_ticket: str = "") -> str:
        if row:
            own = (row.get("ticket") or "").strip()
            if own:
                return own
        ticket = (global_ticket or "").strip()
        return ticket or CREDENTIAL_MISSING

    async def push_targets(self, kind: str, server: str = "") -> list[dict[str, Any]]:
        field = PUSH_FIELD.get(kind)
        if not field:
            return []
        rows = await self.sql.select_all("session_config", f"{field}=?", (1,))
        rows = [row for row in rows if self.is_bot_enabled(row)]
        if kind in GLOBAL_KINDS:
            return rows
        server = (server or "").strip()
        resolver = getattr(self, "resolve_server", None)
        if callable(resolver):
            official = resolver(server)
            if official:
                server = official
        matched = []
        for row in rows:
            bound = (row.get("server") or "").strip()
            if callable(resolver):
                official_bound = resolver(bound)
                if official_bound:
                    bound = official_bound
            if bound == server:
                matched.append(row)
        return matched

    async def servers_with_push(self, kind: str) -> list[str]:
        field = PUSH_FIELD.get(kind)
        if not field:
            return []
        rows = await self.sql.select_all("session_config", f"{field}=?", (1,))
        servers = []
        resolver = getattr(self, "resolve_server", None)
        for row in rows:
            server = (row.get("server") or "").strip()
            if callable(resolver):
                official = resolver(server)
                if official:
                    server = official
            if server and server not in servers:
                servers.append(server)
        return servers

    async def get_push_state(self, kind: str, server: str) -> str:
        row = await self.sql.select_one("push_state", "kind=? AND server=?", (kind, server))
        return "" if not row else str(row.get("status") or "")

    async def set_push_state(self, kind: str, server: str, status: str) -> None:
        row = await self.sql.select_one("push_state", "kind=? AND server=?", (kind, server))
        if row:
            await self.sql.update(
                "push_state",
                {"status": str(status)},
                "kind=? AND server=?",
                (kind, server),
            )
            return
        await self.sql.insert(
            "push_state",
            {"kind": kind, "server": server, "status": str(status)},
        )

    def public_row(self, row: dict[str, Any], has_global_ticket: bool = False, has_global_token: bool = False) -> dict[str, Any]:
        has_own_token = bool((row.get("token") or "").strip())
        use_global_token = bool(row.get("use_global_token"))
        if has_own_token:
            token_status = mask_secret(row.get("token") or "")
        elif use_global_token and has_global_token:
            token_status = "使用全局"
        elif use_global_token:
            token_status = "全局未配置"
        else:
            token_status = "未配置"
        has_own_ticket = bool((row.get("ticket") or "").strip())
        ticket_status = mask_secret(row.get("ticket") or "")
        if not has_own_ticket and has_global_ticket:
            ticket_status = "使用全局"
        return {
            "umo": row.get("umo", ""),
            "display_name": row.get("display_name", ""),
            "server": row.get("server", ""),
            "token_status": token_status,
            "ticket_status": ticket_status,
            "has_token": has_own_token or (use_global_token and has_global_token),
            "has_ticket": has_own_ticket or has_global_ticket,
            "use_global_token": use_global_token,
            "bot_enabled": self.is_bot_enabled(row),
            "push_kaifu": bool(row.get("push_kaifu")),
            "push_xinwen": bool(row.get("push_xinwen")),
            "push_shuma": bool(row.get("push_shuma")),
            "push_chitu": bool(row.get("push_chitu")),
            "pushes": {kind: bool(row.get(field)) for kind, field in PUSH_FIELD.items()},
        }

    async def get_admin(self) -> dict[str, Any] | None:
        return await self.sql.select_one("plugin_admin", "id=?", (1,))

    async def claim_admin(self, user_id: str, name: str = "") -> tuple[bool, str]:
        row = await self.get_admin()
        current = ((row or {}).get("user_id") or "").strip()
        if current and current != user_id:
            return False, (row or {}).get("name") or current
        await self.sql.update(
            "plugin_admin",
            {"user_id": user_id, "name": name, "claimed_at": _now()},
            "id=?",
            (1,),
        )
        return True, name or user_id

    async def is_claimed_admin(self, user_id: str) -> bool:
        row = await self.get_admin()
        current = ((row or {}).get("user_id") or "").strip()
        return bool(current) and current == str(user_id or "").strip()

    def enabled_kinds(self, row: dict[str, Any] | None) -> set[str]:
        if not row:
            return set()
        return {kind for kind, field in PUSH_FIELD.items() if row.get(field)}

    async def enabled_push_kinds(self) -> list[str]:
        kinds = []
        for kind, field in PUSH_FIELD.items():
            rows = await self.sql.select_all("session_config", f"{field}=?", (1,))
            if rows:
                kinds.append(kind)
        return kinds


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
