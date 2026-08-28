# pyright: reportOptionalMemberAccess=false

import asyncio
import aiosqlite
from typing import Any, Dict, List, Optional, Tuple


class AsyncSQLiteDB:
    def __init__(self, db_path: str = "data.db"):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None
        self._write_lock: asyncio.Lock = asyncio.Lock()
        

    # ======================
    # 生命周期
    # ======================
    
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        await self.close()

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path, timeout=15.0)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA synchronous=NORMAL")
        await self.conn.execute("PRAGMA busy_timeout=15000")
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    # ======================
    # 基础执行
    # ======================

    async def execute(self, sql: str, params: Tuple = ()):
        async with self._write_lock:
            async with self.conn.execute(sql, params):
                await self.conn.commit()

    async def execute_many(self, statements: list[tuple[str, Tuple]]) -> None:
        """在同一事务内依次执行多条写语句，任一条失败则整体回滚。"""
        async with self._write_lock:
            await self.conn.execute("BEGIN")
            try:
                for sql, params in statements:
                    await self.conn.execute(sql, params)
                await self.conn.commit()
            except Exception:
                await self.conn.rollback()
                raise

    async def fetch_one(self, sql: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        async with self.conn.execute(sql, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetch_all(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        async with self.conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ======================
    # CRUD
    # ======================

    async def insert(self, table: str, data: Dict[str, Any]):
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
        await self.execute(sql, tuple(data.values()))

    async def update(self, table: str, data: Dict[str, Any], where: str, params: Tuple):
        set_clause = ", ".join([f"{k}=?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        await self.execute(sql, tuple(data.values()) + params)

    async def select_one(self, table: str, where: str = "", params: Tuple = ()):
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        return await self.fetch_one(sql, params)

    async def select_all(self, table: str, where: str = "", params: Tuple = ()):
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        return await self.fetch_all(sql, params)
