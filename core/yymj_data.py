import asyncio
import difflib
import re
import time
import unicodedata
from urllib.parse import urlparse
from typing import Any

import aiohttp
from astrbot.api import logger


class YymjGuideService:
    """隐元秘鉴公众号主页文章索引。"""

    _HOMEPAGE_URL = "https://mp.weixin.qq.com/mp/homepage"
    _HOMEPAGE_PARAMS = {
        "__biz": "MzAwOTM5Mzc1OA==",
        "hid": "14",
        "sn": "c21eb0b71af61de060fded906a8a0be4",
        "scene": "18",
    }
    _CATEGORY_IDS = (0, 1, 2)
    _CACHE_TTL = 6 * 60 * 60
    _ALLOWED_LINK_HOSTS = {"mp.weixin.qq.com"}
    _ALLOWED_IMAGE_HOSTS = {"mmbiz.qpic.cn", "mmbiz.qlogo.cn"}

    def __init__(self, timeout: int = 10):
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._articles: list[dict[str, Any]] | None = None
        self._cached_at = 0.0
        self._refresh_lock = asyncio.Lock()

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    @staticmethod
    def _https_url(value: Any) -> str:
        return str(value or "").strip().replace("http://", "https://", 1)

    @classmethod
    def _safe_url(cls, value: Any, allowed_hosts: set[str]) -> str:
        url = cls._https_url(value)
        if not url:
            return ""
        parsed = urlparse(url)
        return url if parsed.scheme == "https" and parsed.hostname in allowed_hosts else ""

    async def _fetch_category(self, category_id: int) -> list[dict[str, Any]]:
        session = await self._get_session()
        params = {
            **self._HOMEPAGE_PARAMS,
            "cid": str(category_id),
            "begin": "0",
            "count": "100",
            "action": "appmsg_list",
            "f": "json",
            "appmsg_token": "",
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
                "MicroMessenger/8.0.49"
            ),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self._safe_url(self._HOMEPAGE_URL, self._ALLOWED_LINK_HOSTS),
        }
        async with session.post(self._HOMEPAGE_URL, params=params, headers=headers) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
        if not isinstance(payload, dict) or not isinstance(payload.get("base_resp"), dict):
            raise ValueError("公众号主页响应格式异常")
        if int(payload["base_resp"].get("ret") or 0) != 0:
            raise ValueError(f"公众号主页接口返回 {payload['base_resp'].get('ret')}")
        rows = payload.get("appmsg_list") or []
        return [row for row in rows if isinstance(row, dict) and row.get("link")]

    async def _load_articles(self) -> list[dict[str, Any]]:
        async with self._refresh_lock:
            now = time.monotonic()
            if self._articles is not None and now - self._cached_at < self._CACHE_TTL:
                return self._articles

            responses = await asyncio.gather(
                *(self._fetch_category(category_id) for category_id in self._CATEGORY_IDS),
                return_exceptions=True,
            )
            rows: list[dict[str, Any]] = []
            errors: list[str] = []
            for category_id, response in zip(self._CATEGORY_IDS, responses):
                if isinstance(response, BaseException):
                    errors.append(f"cid={category_id}: {response}")
                    continue
                rows.extend(response)

            if errors:
                logger.warning(f"部分公众号攻略分类获取失败: {'; '.join(errors)}")
                if self._articles is not None:
                    return self._articles
                raise RuntimeError("获取公众号攻略失败")
            if not rows:
                logger.error("获取公众号攻略失败: 所有分类均无数据")
                raise RuntimeError("获取公众号攻略失败")

            deduped: dict[str, dict[str, Any]] = {}
            for row in rows:
                aid = str(row.get("aid") or row.get("link") or "")
                if aid not in deduped:
                    deduped[aid] = row
            self._articles = list(deduped.values())
            self._cached_at = now
            return self._articles

    @staticmethod
    def _normalize(text: Any) -> str:
        value = unicodedata.normalize("NFKC", str(text or "")).lower()
        return re.sub(r"\s+", "", value)

    @staticmethod
    def _title_names(title: str) -> list[str]:
        names = re.findall(r"[【\[]([^】\]]+)[】\]]", title)
        if names:
            return [name.strip() for name in names if name.strip()]
        head = re.split(r"[（(]", title, maxsplit=1)[0]
        return [head.strip()] if head.strip() else []

    @classmethod
    def _score(cls, row: dict[str, Any], query: str) -> float:
        title = cls._normalize(row.get("title"))
        if not title:
            return 0.0
        names = [cls._normalize(name) for name in cls._title_names(str(row.get("title") or ""))]
        scores = [0.0]
        for name in names:
            if not name:
                continue
            if name == query:
                scores.append(100.0)
            elif name.startswith(query) or query.startswith(name):
                scores.append(80.0)
            elif query in name:
                scores.append(60.0)
            elif name in query:
                scores.append(40.0)
        if title == query:
            scores.append(95.0)
        elif title.startswith(query) or query.startswith(title):
            scores.append(70.0)
        elif query in title:
            scores.append(50.0)
        elif title in query:
            scores.append(30.0)
        ratio = difflib.SequenceMatcher(None, query, title).ratio()
        if ratio >= 0.7:
            scores.append(10.0 + ratio * 20.0)
        return max(scores)

    async def qiyugonglue(self, name: str) -> dict[str, Any]:
        """按名称查找公众号奇遇攻略并返回卡片字段。"""
        query = str(name or "").strip()
        if not query:
            return {"code": 400, "msg": "请指定奇遇名称"}
        try:
            rows = await self._load_articles()
        except Exception:
            logger.exception("获取公众号攻略失败")
            return {"code": 500, "msg": "获取公众号攻略失败"}

        candidates: list[tuple[float, int, dict[str, Any]]] = []
        for row in rows:
            if not self._safe_url(row.get("link"), self._ALLOWED_LINK_HOSTS):
                continue
            score = self._score(row, self._normalize(query))
            if score <= 0:
                continue
            try:
                send_time = int(row.get("sendtime") or 0)
            except (TypeError, ValueError):
                send_time = 0
            candidates.append((score, send_time, row))
        if not candidates:
            return {"code": 404, "msg": "未找到该奇遇的公众号攻略"}

        candidates.sort(
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        row = candidates[0][2]
        return {
            "code": 200,
            "data": {
                "title": str(row.get("title") or query).strip(),
                "desc": str(row.get("digest") or "来源：隐元秘鉴").strip(),
                "url": self._safe_url(row.get("link"), self._ALLOWED_LINK_HOSTS),
                "image": self._safe_url(row.get("cover"), self._ALLOWED_IMAGE_HOSTS),
                "author": str(row.get("author") or "隐元秘鉴").strip(),
            },
        }
