"""unua.top 推栏数据源：角色在线状态与属性查询。"""

import hashlib
import json
import logging
import secrets
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

UNUA_BASE = "https://jx3.unua.top"


class UnuaService:
    """jx3.unua.top 推栏数据接口封装（含 proof 认证）。"""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
        self._proof_ctx: Optional[dict] = None
        self._proof_ts = 0.0

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
        rr = data.get("resolvedRole")
        if isinstance(rr, dict) and rr.get("roleid"):
            return rr
        profile = data.get("profile")
        if isinstance(profile, dict) and profile.get("roleid"):
            return profile
        return None

    def role_online(self, server: str, name: str, tong_name: str = "") -> Dict[str, Any]:
        """查询角色在线状态。 tong_name 由调用方从 JX3API 补充。"""
        return_data: Dict[str, Any] = {"code": 0, "data": "", "msg": "功能函数未执行"}
        rr = self._resolve_role(server, name)
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
        data = self._post("/api/player/role-online", payload)
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

    async def role_attribute(self, server: str, name: str, template: str = "",
                              tong_name: str = "", card_url: str = "") -> Dict[str, Any]:
        """查询角色属性（取最近一场竞技场数据），返回模板渲染所需的结构化数据。"""
        return_data: Dict[str, Any] = {"code": 0, "data": "", "msg": "功能函数未执行"}
        data = self._post("/api/player/home-page", {"roleName": name, "server": server, "mode": "local"})
        if not data:
            return_data["msg"] = "未查询到该角色，请确认区服与角色名"
            return return_data
        profile = data.get("profile") or {}
        matches = data.get("data") or []
        if not matches:
            return_data["msg"] = "未查询到该角色的战绩数据"
            return return_data
        player = None
        match_id = None
        for m in matches[:3]:
            mid = m.get("match_id")
            match = self._post("/api/match/detail", {"match_id": mid})
            if not match:
                continue
            for team in match.get("teams") or []:
                for p in team.get("players") or []:
                    if p.get("name") == name:
                        player = p
                        match_id = mid
                        break
                if player:
                    break
            if player:
                break
        if not player:
            return_data["msg"] = "未在最近战绩中找到该角色的属性数据"
            return return_data
        return_data["data"] = {
            "roleName": name,
            "server": profile.get("server") or "",
            "zone": data.get("resolvedRole", {}).get("zone") or "",
            "faction": profile.get("faction") or "",
            "kungfu": profile.get("kungfu") or "",
            "bodyType": profile.get("bodyType") or "",
            "camp": profile.get("camp") or "",
            "tongName": tong_name,
            "cardUrl": card_url,
            "avatar": profile.get("avatar") or "",
            "matchId": match_id,
            "qualities": player.get("qualities") or [],
            "equipments": player.get("equipments") or [],
            "talents": player.get("talents") or [],
            "stats": profile.get("stats") or [],
            "playerStats": player.get("stats") or {},
        }
        return_data["code"] = 200
        if template:
            from .template import load_template
            return_data["temp"] = await load_template(template)
        return return_data

    def close(self):
        try:
            self._session.close()
        except Exception:
            pass
