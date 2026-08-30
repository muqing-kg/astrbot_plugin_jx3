from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from .event_catalog import (
    ACTION_IDS,
    GLOBAL_ACTIONS,
    KIND_ACTIONS,
    LEGACY_PUSH_FIELDS,
)
from .session_policy import (
    CREDENTIAL_MISSING,
    NEED_TICKET,
    NEED_TOKEN,
    UNBOUND_SERVER,
    is_group_umo,
    mask_secret,
    resolve_query_server,
)
from .sqlite import AsyncSQLiteDB


__all__ = [
    "CREDENTIAL_MISSING",
    "NEED_TICKET",
    "NEED_TOKEN",
    "UNBOUND_SERVER",
    "SessionStore",
    "mask_secret",
    "resolve_query_server",
]


class SessionStore:
    def __init__(self, sqlite: AsyncSQLiteDB):
        self.sql = sqlite
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._push_state_lock = asyncio.Lock()

    def session_lock(self, umo: str) -> asyncio.Lock:
        key = str(umo or "").strip()
        if key not in self._session_locks:
            self._session_locks[key] = asyncio.Lock()
        return self._session_locks[key]

    async def init(self) -> None:
        await self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS session_config (
                umo TEXT PRIMARY KEY,
                display_name TEXT DEFAULT '',
                server TEXT DEFAULT '',
                token TEXT DEFAULT '',
                push_token TEXT DEFAULT '',
                ticket TEXT DEFAULT '',
                use_global_token INTEGER DEFAULT 0,
                use_global_push_token INTEGER DEFAULT 0,
                is_private INTEGER DEFAULT 0,
                claim_identity TEXT DEFAULT '',
                claim_type TEXT DEFAULT 'claimant',
                claim_name TEXT DEFAULT '',
                claim_at TEXT DEFAULT '',
                bot_enabled INTEGER DEFAULT 1,
                llm_enabled INTEGER DEFAULT 1,
                push_fail_count INTEGER DEFAULT 0,
                push_last_error TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            )
            """
        )
        extra_columns = [
            "push_token TEXT DEFAULT ''",
            "use_global_push_token INTEGER DEFAULT 0",
            "bot_enabled INTEGER DEFAULT 1",
            "llm_enabled INTEGER DEFAULT 1",
            "push_fail_count INTEGER DEFAULT 0",
            "push_last_error TEXT DEFAULT ''",
            "is_private INTEGER DEFAULT 0",
            "claim_identity TEXT DEFAULT ''",
            "claim_type TEXT DEFAULT 'claimant'",
            "claim_name TEXT DEFAULT ''",
            "claim_at TEXT DEFAULT ''",
        ]
        for column in extra_columns:
            try:
                await self.sql.execute(
                    f"ALTER TABLE session_config ADD COLUMN {column}"
                )
            except Exception:
                pass
        await self.sql.execute(
            "UPDATE session_config SET claim_type='astrbot_admin' "
            "WHERE TRIM(claim_identity)=''"
        )
        await self.sql.execute(
            "UPDATE session_config SET claim_type='claimant' "
            "WHERE TRIM(claim_identity)<>'' AND TRIM(COALESCE(claim_type,''))=''"
        )
        await self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY,
                completed_at TEXT NOT NULL
            )
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
        push_state_columns = {
            str(row.get("name") or "")
            for row in await self.sql.fetch_all("PRAGMA table_info(push_state)")
        }
        if "token_key" not in push_state_columns:
            await self.sql.execute(
                """
                CREATE TABLE push_state_token_v1 (
                    kind TEXT NOT NULL,
                    server TEXT NOT NULL,
                    token_key TEXT NOT NULL,
                    status TEXT DEFAULT '',
                    PRIMARY KEY (kind, server, token_key)
                )
                """
            )
            await self.sql.execute(
                """
                INSERT INTO push_state_token_v1 (kind, server, token_key, status)
                SELECT kind, server, '__scheduled__', status FROM push_state
                """
            )
            await self.sql.execute("DROP TABLE push_state")
            await self.sql.execute(
                "ALTER TABLE push_state_token_v1 RENAME TO push_state"
            )
        await self.sql.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_push_state_token
            ON push_state (token_key, kind, server)
            """
        )
        await self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS session_push_events (
                umo TEXT NOT NULL,
                action TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (umo, action)
            )
            """
        )
        event_columns = {
            str(row.get("name") or "")
            for row in await self.sql.fetch_all("PRAGMA table_info(session_push_events)")
        }
        if "enabled" in event_columns:
            await self.sql.execute(
                "DELETE FROM session_push_events WHERE enabled=0"
            )
            try:
                await self.sql.execute(
                    "ALTER TABLE session_push_events DROP COLUMN enabled"
                )
            except Exception:
                pass
        await self.sql.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_session_push_events_action
            ON session_push_events (action, umo)
            """
        )
        migration_row = await self.sql.select_one(
            "schema_migrations", "name=?", ("independent_push_events_v1",)
        )
        if not migration_row:
            columns = {
                str(row.get("name") or "")
                for row in await self.sql.fetch_all("PRAGMA table_info(session_config)")
            }
            for kind, field in LEGACY_PUSH_FIELDS.items():
                if field not in columns:
                    continue
                rows = await self.sql.select_all("session_config", f"{field}=1")
                for row in rows:
                    umo = str(row.get("umo") or "")
                    if not umo:
                        continue
                    for action in KIND_ACTIONS.get(kind, []):
                        await self.sql.execute(
                            """
                            INSERT OR IGNORE INTO session_push_events
                            (umo, action, updated_at)
                            VALUES (?, ?, ?)
                            """,
                            (umo, action, _now()),
                        )
            await self.sql.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (name, completed_at)
                VALUES (?, ?)
                """,
                ("independent_push_events_v1", _now()),
            )
        state_migration_row = await self.sql.select_one(
            "schema_migrations", "name=?", ("legacy_push_state_actions_v1",)
        )
        if not state_migration_row:
            old_push_states = await self.sql.select_all("push_state")
            legacy_state_kinds = sorted({
                str(state.get("kind") or "").strip()
                for state in old_push_states
                if str(state.get("kind") or "").strip() not in ACTION_IDS
            })
            for old_kind in legacy_state_kinds:
                for state in [item for item in old_push_states if str(item.get("kind") or "").strip() == old_kind]:
                    await self.sql.execute(
                        "DELETE FROM push_state WHERE kind=? AND server=? AND token_key=?",
                        (old_kind, state.get("server"), state.get("token_key")),
                    )
                    for action in KIND_ACTIONS.get(old_kind, []):
                        await self.sql.execute(
                            """
                            INSERT OR IGNORE INTO push_state
                            (kind, server, token_key, status)
                            VALUES (?, ?, '__scheduled__', ?)
                            """,
                            (action, state.get("server"), state.get("status")),
                        )
            await self.sql.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (name, completed_at)
                VALUES (?, ?)
                """,
                ("legacy_push_state_actions_v1", _now()),
            )
        await self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_claimants (
                user_id TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                claimed_at TEXT DEFAULT ''
            )
            """
        )
        try:
            old_admin = await self.sql.select_one("plugin_admin", "id=?", (1,))
        except Exception:
            old_admin = None
        try:
            old_claims = await self.sql.fetch_all(
                "SELECT claim_identity, claim_name, claim_at FROM session_config "
                "WHERE TRIM(claim_identity) <> '' AND TRIM(claim_identity) <> 'ASTRBOT_ADMIN' GROUP BY claim_identity"
            )
        except Exception:
            old_claims = []
        for claim in old_claims:
            old_user_id = str(claim.get("claim_identity") or "").strip()
            if not old_user_id:
                continue
            await self.sql.execute(
                """
                INSERT OR IGNORE INTO plugin_claimants (user_id, name, claimed_at)
                VALUES (?, ?, ?)
                """,
                (
                    old_user_id,
                    str(claim.get("claim_name") or "").strip(),
                    str(claim.get("claim_at") or "").strip() or _now(),
                ),
            )
        if old_admin:
            old_user_id = str(old_admin.get("user_id") or "").strip()
            if old_user_id:
                old_name = str(old_admin.get("name") or "").strip()
                old_at = str(old_admin.get("claimed_at") or "").strip()
                await self.sql.execute(
                    """
                    INSERT OR IGNORE INTO plugin_claimants (user_id, name, claimed_at)
                    VALUES (?, ?, ?)
                    """,
                    (old_user_id, old_name, old_at or _now()),
                )
            await self.sql.execute("DROP TABLE plugin_admin")
        await self.sql.execute(
            """
            CREATE TABLE IF NOT EXISTS session_managers (
                umo TEXT NOT NULL,
                user_id TEXT NOT NULL,
                name TEXT DEFAULT '',
                created_at TEXT DEFAULT '',
                PRIMARY KEY (umo, user_id)
            )
            """
        )
        await self.sql.execute(
            """
            DELETE FROM session_push_events
            WHERE NOT EXISTS (
                SELECT 1
                FROM session_config
                WHERE session_config.umo=session_push_events.umo
            )
            """
        )
        # 插件功能只面向群聊。历史私聊会话不再保留。
        await self.sql.execute("DELETE FROM session_config WHERE is_private=1")
        await self.sql.execute(
            "DELETE FROM session_managers WHERE NOT EXISTS ("
            "SELECT 1 FROM session_config WHERE session_config.umo=session_managers.umo)"
        )

    async def ensure(self, umo: str, display_name: str = "", is_private: bool = False) -> dict[str, Any]:
        if is_private or not is_group_umo(umo):
            return {}
        row = await self.get(umo)
        if row:
            updates = {}
            if display_name and row.get("display_name") != display_name:
                updates["display_name"] = display_name
            if bool(row.get("is_private")) != bool(is_private):
                updates["is_private"] = 1 if is_private else 0
            if updates:
                updates["updated_at"] = _now()
                await self.sql.update(
                    "session_config",
                    updates,
                    "umo=?",
                    (umo,),
                )
                row.update(updates)
            return row
        await self.sql.execute(
            """
            INSERT OR IGNORE INTO session_config (
                umo, display_name, is_private, server, token, ticket,
                use_global_token, bot_enabled, updated_at
            ) VALUES (?, ?, ?, '', '', '', 0, 1, ?)
            """,
            (umo, display_name, 1 if is_private else 0, _now()),
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
        return [
            row for row in rows
            if (row.get("server") or "").strip() and is_group_umo(row.get("umo", ""))
        ]

    async def bind_server(self, umo: str, server: str, display_name: str = "", is_private: bool = False) -> dict[str, Any]:
        if is_private or not is_group_umo(umo):
            raise ValueError("本插件只支持群聊会话绑定")
        await self.ensure(umo, display_name, is_private)
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
        async with self.session_lock(umo):
            row = await self.ensure(umo)
            await self.sql.execute(
                "DELETE FROM session_push_events WHERE umo=?",
                (umo,),
            )
            if row:
                await self.sql.update(
                    "session_config",
                    {
                        "server": "",
                        "updated_at": _now(),
                    },
                    "umo=?",
                    (umo,),
                )
        return await self.get(umo)

    async def set_push(self, umo: str, action: str, enabled: bool) -> tuple[bool, str]:
        action = str(action or "").strip()
        if action not in ACTION_IDS:
            return False, "不支持的推送类型"
        async with self.session_lock(umo):
            row = await self.ensure(umo)
            if not row:
                return False, "会话不存在"
            if enabled and action not in GLOBAL_ACTIONS and not (row.get("server") or "").strip():
                return False, "请先绑定区服后再打开推送。"
            if enabled:
                await self.sql.execute(
                    """
                    INSERT INTO session_push_events (umo, action, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(umo, action) DO UPDATE SET
                        updated_at=excluded.updated_at
                    """,
                    (umo, action, _now()),
                )
            else:
                await self.sql.execute(
                    "DELETE FROM session_push_events WHERE umo=? AND action=?",
                    (umo, action),
                )
            await self.sql.update(
                "session_config",
                {"updated_at": _now()},
                "umo=?",
                (umo,),
            )
        return True, ""

    async def set_token(self, umo: str, token: str) -> None:
        if not is_group_umo(umo):
            raise ValueError("本插件只支持群聊会话配置 Token")
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"token": token.strip(), "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def set_ticket(self, umo: str, ticket: str) -> None:
        if not is_group_umo(umo):
            raise ValueError("本插件只支持群聊会话配置推栏标识")
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"ticket": ticket.strip(), "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def set_bot_enabled(self, umo: str, enabled: bool) -> None:
        if not is_group_umo(umo):
            raise ValueError("本插件只支持群聊会话开关")
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

    async def set_llm_enabled(self, umo: str, enabled: bool) -> None:
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"llm_enabled": 1 if enabled else 0, "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def set_push_token(self, umo: str, token: str) -> None:
        if not is_group_umo(umo):
            raise ValueError("本插件只支持群聊会话配置推送令牌")
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"push_token": token.strip(), "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    def is_llm_enabled(self, row: dict[str, Any] | None) -> bool:
        if not row:
            return True
        if "llm_enabled" not in row or row.get("llm_enabled") is None:
            return True
        return bool(row.get("llm_enabled"))

    async def delete_session(self, umo: str) -> bool:
        if not is_group_umo(umo):
            raise ValueError("只能删除群聊会话")
        async with self.session_lock(umo):
            async with self._push_state_lock:
                row = await self.get(umo)
                if not row:
                    return False
                await self.sql.execute("DELETE FROM session_config WHERE umo=?", (umo,))
                await self.sql.execute("DELETE FROM session_managers WHERE umo=?", (umo,))
                await self.sql.execute("DELETE FROM session_push_events WHERE umo=?", (umo,))
                for state in await self.sql.select_all("push_state"):
                    action = str(state.get("kind") or "")
                    server = str(state.get("server") or "")
                    if action in ACTION_IDS and not await self.push_targets(action, server):
                        await self.sql.execute(
                            "DELETE FROM push_state WHERE kind=? AND server=?",
                            (action, server),
                        )
            self._session_locks.pop(umo, None)
            return True

    async def is_active_push_target(self, umo: str, action: str) -> bool:
        action = str(action or "").strip()
        if action not in ACTION_IDS or not is_group_umo(umo):
            return False
        row = await self.get(umo)
        if not row or not self.is_bot_enabled(row):
            return False
        event = await self.sql.select_one(
            "session_push_events",
            "umo=? AND action=?",
            (umo, action),
        )
        return bool(event)

    async def mark_push_success(self, umo: str) -> None:
        if not is_group_umo(umo):
            return
        row = await self.get(umo)
        if not row or (
            not int(row.get("push_fail_count") or 0)
            and not str(row.get("push_last_error") or "").strip()
        ):
            return
        await self.sql.update(
            "session_config",
            {"push_fail_count": 0, "push_last_error": "", "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def record_permanent_push_failure(self, umo: str, detail: str) -> None:
        if not is_group_umo(umo):
            return
        row = await self.get(umo)
        if not row:
            return
        count = int(row.get("push_fail_count") or 0) + 1
        detail = str(detail or "").strip()[:500]
        await self.sql.update(
            "session_config",
            {"push_fail_count": count, "push_last_error": detail, "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def set_use_global_token(self, umo: str, enabled: bool) -> None:
        if not is_group_umo(umo):
            raise ValueError("本插件只支持群聊会话配置")
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"use_global_token": 1 if enabled else 0, "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def set_use_global_push_token(self, umo: str, enabled: bool) -> None:
        if not is_group_umo(umo):
            raise ValueError("本插件只支持群聊会话配置")
        await self.ensure(umo)
        await self.sql.update(
            "session_config",
            {"use_global_push_token": 1 if enabled else 0, "updated_at": _now()},
            "umo=?",
            (umo,),
        )

    async def clear_secret(self, umo: str, kind: str) -> None:
        if kind not in ("token", "push_token", "ticket"):
            raise ValueError(f"不支持的密钥类型: {kind}")
        if not is_group_umo(umo):
            raise ValueError("本插件只支持群聊会话配置")
        field = {
            "token": "token",
            "push_token": "push_token",
            "ticket": "ticket",
        }[kind]
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

    def resolve_push_token(self, row: dict[str, Any] | None, global_push_token: str = "") -> str:
        own = str((row or {}).get("push_token") or "").strip()
        if own:
            return own
        if not (row or {}).get("use_global_push_token"):
            return CREDENTIAL_MISSING
        global_token = (global_push_token or "").strip()
        return global_token or CREDENTIAL_MISSING

    async def push_targets(self, action: str, server: str = "") -> list[dict[str, Any]]:
        action = str(action or "").strip()
        if action not in ACTION_IDS:
            return []
        rows = await self.rows_with_push_action(action)
        if action in GLOBAL_ACTIONS:
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

    async def rows_with_push_action(self, action: str) -> list[dict[str, Any]]:
        action = str(action or "").strip()
        if action not in ACTION_IDS:
            return []
        rows = await self.sql.fetch_all(
            """
            SELECT session_config.*
            FROM session_config
            JOIN session_push_events
              ON session_push_events.umo=session_config.umo
            WHERE session_push_events.action=?
              AND session_config.bot_enabled=1
            """,
            (action,),
        )
        return [
            row for row in rows
            if self.is_bot_enabled(row) and is_group_umo(row.get("umo", ""))
        ]

    async def servers_with_push(self, action: str) -> list[str]:
        action = str(action or "").strip()
        if action not in ACTION_IDS:
            return []
        rows = await self.sql.fetch_all(
            """
            SELECT session_config.*
            FROM session_config
            JOIN session_push_events
              ON session_push_events.umo=session_config.umo
            WHERE session_push_events.action=?
              AND session_config.bot_enabled=1
            """,
            (action,),
        )
        servers = []
        resolver = getattr(self, "resolve_server", None)
        for row in rows:
            if not self.is_bot_enabled(row) or not is_group_umo(row.get("umo", "")):
                continue
            server = (row.get("server") or "").strip()
            if callable(resolver):
                official = resolver(server)
                if official:
                    server = official
            if server and server not in servers:
                servers.append(server)
        return servers

    async def get_push_state(self, action: str, server: str, token_key: str = "__scheduled__") -> str:
        row = await self.sql.select_one(
            "push_state",
            "kind=? AND server=? AND token_key=?",
            (action, server, token_key),
        )
        return "" if not row else str(row.get("status") or "")

    async def set_push_state(
        self,
        action: str,
        server: str,
        status: str,
        token_key: str = "__scheduled__",
    ) -> None:
        async with self._push_state_lock:
            action = str(action or "").strip()
            if action not in ACTION_IDS or not await self.push_targets(action, server):
                return
            row = await self.sql.select_one(
                "push_state",
                "kind=? AND server=? AND token_key=?",
                (action, server, token_key),
            )
            if row:
                await self.sql.update(
                    "push_state",
                    {"status": str(status)},
                    "kind=? AND server=? AND token_key=?",
                    (action, server, token_key),
                )
                return
            await self.sql.insert(
                "push_state",
                {"kind": action, "server": server, "token_key": token_key, "status": str(status)},
            )

    def public_row(
        self,
        row: dict[str, Any],
        has_global_ticket: bool = False,
        has_global_token: bool = False,
        has_global_push_token: bool = False,
        global_token: str = "",
        global_ticket: str = "",
        global_push_token: str = "",
    ) -> dict[str, Any]:
        own_token = (row.get("token") or "").strip()
        own_push_token = (row.get("push_token") or "").strip()
        own_ticket = (row.get("ticket") or "").strip()
        global_token = (global_token or "").strip()
        global_ticket = (global_ticket or "").strip()
        global_push_token = (global_push_token or "").strip()
        has_own_token = bool(own_token)
        token_global_available = bool(global_token) or has_global_token
        ticket_global_available = bool(global_ticket) or has_global_ticket
        use_global_token = bool(row.get("use_global_token"))
        use_global_push_token = bool(row.get("use_global_push_token"))
        token_display_value = own_token or (global_token if use_global_token else "")
        if has_own_token:
            token_status = own_token
        elif use_global_token and token_global_available:
            token_status = "使用全局"
        elif use_global_token:
            token_status = "全局未配置"
        else:
            token_status = "未配置"
        if has_own_token and use_global_token and token_global_available:
            token_source = "all"
        elif has_own_token:
            token_source = "group"
        elif use_global_token and token_global_available:
            token_source = "global"
        else:
            token_source = "none"
        has_own_ticket = bool(own_ticket)
        ticket_display_value = own_ticket or global_ticket
        if has_own_ticket:
            ticket_status = own_ticket
        elif ticket_global_available:
            ticket_status = "使用全局"
        else:
            ticket_status = "未配置"
        return {
            "umo": row.get("umo", ""),
            "display_name": row.get("display_name", ""),
            "server": row.get("server", ""),
            "token_status": token_status,
            "ticket_status": ticket_status,
            "token_value": own_token,
            "token_display_value": token_display_value,
            "ticket_value": own_ticket,
            "ticket_display_value": ticket_display_value,
            "global_token_value": global_token,
            "global_ticket_value": global_ticket,
            "has_token": has_own_token or (use_global_token and token_global_available),
            "has_ticket": has_own_ticket or ticket_global_available,
            "use_global_token": use_global_token,
            "token_source": token_source,
            "push_token_status": (
                own_push_token
                or ("使用全局" if use_global_push_token and has_global_push_token else "全局未配置" if use_global_push_token else "未配置")
            ),
            "push_token_value": own_push_token,
            "push_token_display_value": own_push_token or (global_push_token if use_global_push_token else ""),
            "global_push_token_value": global_push_token,
            "has_push_token": bool(own_push_token or (use_global_push_token and global_push_token)),
            "use_global_push_token": use_global_push_token,
            "push_token_source": (
                "all" if own_push_token and use_global_push_token and global_push_token
                else "group" if own_push_token
                else "global" if use_global_push_token and global_push_token
                else "none"
            ),
            "bot_enabled": self.is_bot_enabled(row),
            "push_fail_count": int(row.get("push_fail_count") or 0),
            "push_last_error": row.get("push_last_error", ""),
            "claim_identity": row.get("claim_identity", ""),
            "claim_type": str(row.get("claim_type") or ("astrbot_admin" if not row.get("claim_identity") else "claimant")),
            "claim_name": row.get("claim_name", ""),
            "managers": [],
        }

    async def claim_admin(self, user_id: str, name: str = "") -> tuple[bool, str]:
        user_id = str(user_id or "").strip()
        if not user_id:
            return False, "未识别到用户身份。"
        name = str(name or "").strip()
        row = await self.sql.select_one("plugin_claimants", "user_id=?", (user_id,))
        if row:
            if name:
                await self.sql.update(
                    "plugin_claimants",
                    {"name": name, "claimed_at": _now()},
                    "user_id=?",
                (user_id,),
            )
            return True, name or str(row.get("name") or "") or user_id
        await self.sql.execute(
            """
            INSERT OR IGNORE INTO plugin_claimants (user_id, name, claimed_at)
            VALUES (?, ?, ?)
            """,
            (user_id, name, _now()),
        )
        row = await self.sql.select_one("plugin_claimants", "user_id=?", (user_id,))
        return True, name or str((row or {}).get("name") or "") or user_id

    async def is_claimed_admin(self, user_id: str) -> bool:
        user_id = str(user_id or "").strip()
        if not user_id:
            return False
        return bool(await self.sql.select_one("plugin_claimants", "user_id=?", (user_id,)))

    async def mark_astrbot_admin_claims(self, admin_ids: list[str] | tuple[str, ...]) -> None:
        for admin_id in admin_ids:
            identity = str(admin_id or "").strip()
            if not identity:
                continue
            await self.sql.execute(
                "UPDATE session_config SET claim_type='astrbot_admin' WHERE claim_identity=?",
                (identity,),
            )
            await self.sql.execute(
                "DELETE FROM plugin_claimants WHERE user_id=?",
                (identity,),
            )

    async def get_session_identity(self, umo: str) -> dict[str, Any]:
        row = await self.get(umo) or {}
        return {
            "identity": str(row.get("claim_identity") or "").strip(),
            "name": str(row.get("claim_name") or "").strip(),
            "at": str(row.get("claim_at") or "").strip(),
        }

    async def set_session_claim(
        self,
        umo: str,
        identity: str,
        name: str = "",
        claim_type: str = "claimant",
    ) -> dict[str, Any]:
        await self.ensure(umo)
        identity = str(identity or "").strip()
        if not identity:
            return await self.get(umo)
        await self.sql.execute(
            """
            UPDATE session_config
            SET claim_identity=?, claim_type=?, claim_name=?, claim_at=?, updated_at=?
            WHERE umo=? AND (claim_identity IS NULL OR TRIM(claim_identity)='')
            """,
            (
                identity,
                "astrbot_admin" if claim_type == "astrbot_admin" else "claimant",
                str(name or "").strip(),
                _now(),
                _now(),
                umo,
            ),
        )
        row = await self.get(umo) or {}
        if (
            str(row.get("claim_identity") or "").strip() == identity
            and str(row.get("claim_type") or "") != "astrbot_admin"
        ):
            await self.claim_admin(identity, name)
        return row

    async def clear_claimant(self, identity: str) -> None:
        identity = str(identity or "").strip()
        if not identity:
            return
        await self.sql.execute("DELETE FROM plugin_claimants WHERE user_id=?", (identity,))
        await self.sql.update(
            "session_config",
            {
                "claim_identity": "",
                "claim_type": "",
                "claim_name": "",
                "claim_at": "",
                "updated_at": _now(),
            },
            "claim_identity=?",
            (identity,),
        )

    async def is_session_owner(self, umo: str, user_id: str, name: str = "") -> bool:
        claim = await self.get_session_identity(umo)
        identity = claim.get("identity") or ""
        if not identity:
            return False
        user_id = str(user_id or "").strip()
        if identity == user_id:
            return True
        return False

    async def list_managers(self, umo: str) -> list[dict[str, Any]]:
        if not umo:
            return []
        return await self.sql.select_all(
            "session_managers",
            "umo=? ORDER BY created_at ASC, user_id ASC",
            (umo,),
        )

    async def add_manager(self, umo: str, user_id: str, name: str = "") -> tuple[bool, str]:
        umo = str(umo or "").strip()
        user_id = str(user_id or "").strip()
        if not umo or not user_id:
            return False, "未识别到被授权人，请直接 @ 成员后发送 授权管理。"
        name = str(name or "").strip()
        claim = await self.get_session_identity(umo)
        identity = claim.get("identity") or ""
        if identity and user_id == identity:
            return False, "认领人已是本会话管理员，无需重复授权。"
        for row in await self.list_managers(umo):
            row_id = str(row.get("user_id") or "").strip()
            if user_id == row_id:
                return False, "该用户已是本会话授权管理员。"
        await self.sql.insert(
            "session_managers",
            {"umo": umo, "user_id": user_id, "name": name, "created_at": _now()},
        )
        return True, name or user_id

    async def remove_manager(self, umo: str, index: int) -> tuple[bool, str]:
        try:
            index = int(index)
        except (TypeError, ValueError):
            return False, "请发送: 「 删除管理 序号 」"
        claim = await self.get_session_identity(umo)
        rows = await self.list_managers(umo)
        offset = 0
        if claim.get("identity"):
            if index <= 1:
                return False, "认领人不可被删除。"
            offset = 1
        target = index - 1 - offset
        if target < 0 or target >= len(rows):
            return False, "序号不存在，请先发送查看管理确认序号。"
        row = rows[target]
        label = str(row.get("name") or row.get("user_id") or "已授权管理员")
        await self.sql.execute(
            "DELETE FROM session_managers WHERE umo=? AND user_id=?",
            (umo, str(row.get("user_id") or "")),
        )
        return True, f"已删除管理员：{label}"

    async def replace_managers(
        self,
        umo: str,
        values: list[str],
    ) -> tuple[bool, str]:
        umo = str(umo or "").strip()
        claim = await self.get_session_identity(umo)
        identity = claim.get("identity") or ""
        claim_name = claim.get("name") or ""
        current = await self.list_managers(umo)
        by_id = {str(row.get("user_id") or "").strip(): row for row in current}
        by_name = {str(row.get("name") or "").strip(): row for row in current}
        desired_ids: list[str] = []
        unknown: list[str] = []
        for value in values or []:
            text = str(value or "").strip().lstrip("@").strip()
            if not text:
                continue
            if identity and text in (identity, claim_name):
                continue
            row = by_id.get(text) or by_name.get(text)
            if not row:
                unknown.append(text)
                continue
            row_id = str(row.get("user_id") or "").strip()
            if row_id and row_id not in desired_ids:
                desired_ids.append(row_id)
        if unknown:
            return False, (
                "无法识别的成员身份：" + "、".join(unknown) + "。\n"
                "已有授权请输入真实 ID、昵称或「昵称（ID）」格式。"
            )
        for row in current:
            row_id = str(row.get("user_id") or "").strip()
            if row_id not in desired_ids:
                await self.sql.execute(
                    "DELETE FROM session_managers WHERE umo=? AND user_id=?",
                    (umo, row_id),
                )
        remain = await self.list_managers(umo)
        labels = [str(row.get("name") or row.get("user_id") or "") for row in remain]
        if labels:
            return True, "已更新授权管理：" + "、".join(labels)
        return True, "已更新授权管理（当前为空）"

    async def is_manager(self, umo: str, user_id: str, name: str = "") -> bool:
        user_id = str(user_id or "").strip()
        if await self.is_session_owner(umo, user_id, name):
            return True
        for row in await self.list_managers(umo):
            row_id = str(row.get("user_id") or "").strip()
            if user_id and user_id == row_id:
                return True
        return False

    async def manager_snapshot(self, umo: str) -> list[dict[str, Any]]:
        rows = []
        claim = await self.get_session_identity(umo)
        if claim.get("identity"):
            rows.append({
                "rank": 1,
                "name": claim.get("name") or "",
                "identity": claim.get("identity") or "",
                "role": "认领人",
            })
        for index, row in enumerate(await self.list_managers(umo), len(rows) + 1):
            rows.append({
                "rank": index,
                "name": row.get("name") or "",
                "identity": row.get("user_id") or "",
                "role": "管理员",
            })
        return rows
    async def enabled_actions(self, umo: str) -> set[str]:
        umo = str(umo or "").strip()
        if not umo:
            return set()
        rows = await self.sql.select_all(
            "session_push_events",
            "umo=?",
            (umo,),
        )
        return {str(row.get("action") or "") for row in rows if str(row.get("action") or "") in ACTION_IDS}

    async def enabled_push_actions(self) -> list[str]:
        rows = await self.sql.fetch_all(
            """
            SELECT DISTINCT session_push_events.action
            FROM session_push_events
            JOIN session_config
              ON session_config.umo=session_push_events.umo
            WHERE session_config.bot_enabled=1
            ORDER BY session_push_events.action
            """
        )
        return [
            str(row.get("action") or "")
            for row in rows
            if str(row.get("action") or "") in ACTION_IDS
        ]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
