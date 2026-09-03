"""unua.top 推栏数据源：角色在线状态查询。"""

import asyncio
import hashlib
import json
import secrets
import time
from typing import Any, Dict, Optional

import requests

from .plugin_log import logger

UNUA_BASE = "https://jx3.unua.top"

class UnuaService:
    """jx3.unua.top 推栏数据接口封装（含 proof 认证）。"""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
        self._proof_ctx: Optional[dict] = None
        self._proof_ts = 0.0
        self._request_lock = asyncio.Lock()

    def _sha256hex(self, data) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def _get_proof(self) -> Optional[dict]:
        now = time.time()
        if self._proof_ctx and now - self._proof_ts < 120:
            return self._proof_ctx
        try:
            r = self._session.get(f"{UNUA_BASE}/api/client-proof", timeout=10)
            r.raise_for_status()
            ctx = r.json()
            self._proof_ctx = ctx
            self._proof_ts = now
            return ctx
        except Exception as e:
            logger.warning(f"unua proof 获取失败: {e}")
            return None

    def _make_headers(self, method: str, path: str, body: str) -> Optional[dict]:
        ctx = self._get_proof()
        if not ctx:
            return None
        token = ctx.get("token", "")
        kid = ctx.get("kid") or ""
        salt = ctx.get("dailySalt") or ""
        aliases = ctx.get("headerAliases") or {}
        clock_offset = (ctx.get("serverTimeMs") or 0) - int(time.time() * 1000)
        ts = str(int((time.time() * 1000 + clock_offset) / 1000))
        nonce = secrets.token_hex(16)[:24]
        daily_part = f":{kid}:{salt}" if kid and salt else ""
        body_hash = self._sha256hex(body)
        proof_str = f"{method.upper()}:{path}:{ts}:{nonce}:{token}:{body_hash}{daily_part}"
        headers = {
            aliases.get("token", "x-client-proof-token"): token,
            aliases.get("timestamp", "x-client-proof-ts"): ts,
            aliases.get("nonce", "x-client-proof-nonce"): nonce,
            aliases.get("proof", "x-client-proof"): self._sha256hex(proof_str),
            aliases.get("bodyHash", "x-client-proof-bodyhash"): body_hash,
        }
        if kid and salt:
            headers[aliases.get("kid", "x-client-proof-kid")] = kid
            headers[aliases.get("daily", "x-client-proof-daily")] = salt
        return headers

    def _post(self, path: str, payload: dict) -> Optional[dict]:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        headers = self._make_headers("POST", path, body)
        if not headers:
            return None
        try:
            r = self._session.post(f"{UNUA_BASE}{path}", data=body.encode("utf-8"), headers=headers, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning(f"unua POST {path} 失败: {e}")
            return None

    def _resolve_role(self, server: str, name: str) -> Optional[dict]:
        data = self._post("/api/player/home-page", {"roleName": name, "server": server, "mode": "local"})
        if not data:
            return None
        rr = data.get("resolvedRole") or {}
        profile = data.get("profile") or {}
        result = dict(rr)
        if isinstance(profile, dict):
            for key in ("faction", "bodyType", "camp", "kungfu"):
                if not result.get(key) and profile.get(key):
                    result[key] = profile[key]
        if isinstance(rr, dict) and rr.get("roleid"):
            return result
        if isinstance(profile, dict) and profile.get("roleid"):
            return result
        return None

    async def role_online(self, server: str, name: str, tong_name: str = "") -> Dict[str, Any]:
        """查询角色在线状态。 tong_name 由调用方从 JX3API 补充。"""
        return_data: Dict[str, Any] = {"code": 0, "data": "", "msg": "功能函数未执行"}
        async with self._request_lock:
            rr = await asyncio.to_thread(self._resolve_role, server, name)
        if not rr:
            return_data["msg"] = "未查询到该角色，请确认区服与角色名"
            return return_data
        payload = {
            "roleId": rr.get("roleid"),
            "gameRoleId": rr.get("roleid"),
            "globalRoleId": rr.get("global_role_id"),
            "gameGlobalRoleId": rr.get("global_role_id"),
            "server": rr.get("server"),
            "zone": rr.get("zone"),
            "centerId": rr.get("personNum"),
        }
        async with self._request_lock:
            data = await asyncio.to_thread(self._post, "/api/player/role-online", payload)
        if not data or not data.get("success"):
            return_data["msg"] = "在线状态查询失败"
            return return_data
        d = data.get("data") or {}
        game = bool(d.get("gameOnline"))
        app = bool(d.get("appOnline"))
        if game:
            status = "游戏在线"
        elif app:
            status = "App在线"
        else:
            status = "离线"
        map_name = str(d.get("mapName") or "").strip()
        lines = [
            f"{rr.get('zone') or ''} · {rr.get('server') or ''} · {name}",
            f"门派体型：{rr.get('faction') or ''} · {rr.get('bodyType') or ''}",
            f"所属阵营：{rr.get('camp') or ''}",
        ]
        if tong_name:
            lines.append(f"所在帮会：{tong_name}")
        lines += [
            f"登录状态：{status}",
            f"角色标识：{d.get('gameRoleId') or rr.get('roleid') or ''}",
        ]
        if game and map_name:
            lines.append(f"所在地图：{map_name}")
        return_data["data"] = "\n".join(lines)
        return_data["code"] = 200
        return return_data

    async def close(self):
        try:
            async with self._request_lock:
                await asyncio.to_thread(self._session.close)
        except Exception:
            pass








