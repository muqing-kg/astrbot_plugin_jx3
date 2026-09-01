# pyright: reportArgumentType=false
import asyncio
import hashlib

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from astrbot.api.event import MessageChain
from astrbot.api.star import Context
from astrbot.api import logger
from astrbot.api import AstrBotConfig

from .event_catalog import FREE_PUSH_ACTIONS, event_dedupe_key, format_event_text, parse_ws_message, resolve_push_action
from .jx3api_data import JX3APIService
from .jx3box_data import JX3BOXService
from .push_errors import is_permanent_group_failure
from .session_policy import CREDENTIAL_MISSING
from .session_store import SessionStore
from .ws_client import DEFAULT_WS_URL, JX3WSClient


class AsyncTask:
    """按会话绑定区服的后台推送。"""

    def __init__(
        self,
        context: Context,
        config: AstrBotConfig,
        jx3api: JX3APIService,
        jx3box: JX3BOXService,
        sessions: SessionStore,
    ):
        self.context = context
        self.conf = config
        self.jx3api = jx3api
        self.jx3box = jx3box
        self.sessions = sessions
        self.scheduler = AsyncIOScheduler()
        self.jobs = {
            "0": {"interval": 60, "name": "赤兔消息"},
        }
        self.ws_clients: dict[str, JX3WSClient] = {}
        logger.info("初始化推送功能成功")

    def _ws_token(self) -> str:
        return str(
            self.conf.get("jx3api_push_token", "")
            or self.conf.get("jx3api_ws_token", "")
            or ""
        ).strip()

    @staticmethod
    def _token_key(token: str) -> str:
        token = (token or "").strip()
        if not token:
            return "__free__"
        return "token:" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]

    async def _push_token_groups(self, event_actions: set[str]) -> dict[str, dict[str, set[str] | str]]:
        groups: dict[str, dict[str, set[str] | str]] = {}
        global_push_token = str(
            self.conf.get("jx3api_push_token", "")
            or self.conf.get("jx3api_ws_token", "")
            or ""
        ).strip()
        for action in event_actions:
            targets = await self.sessions.rows_with_push_action(action)
            for row in targets:
                token = self.sessions.resolve_push_token(row, global_push_token)
                if token == CREDENTIAL_MISSING and action not in FREE_PUSH_ACTIONS:
                    continue
                key = self._token_key("" if token == CREDENTIAL_MISSING else token)
                group = groups.setdefault(key, {"actions": set(), "token": "" if token == CREDENTIAL_MISSING else token})
                cast_set = group["actions"]
                cast_set.add(action)
        return groups

    async def _configure_ws_clients(self, groups: dict[str, dict[str, set[str] | str]]) -> None:
        url = str(self.conf.get("jx3api_ws_url", "") or DEFAULT_WS_URL)
        for key in list(self.ws_clients):
            if key not in groups:
                await self.ws_clients.pop(key).stop()
        for key, group in groups.items():
            actions = group["actions"]
            token = str(group["token"] or "")
            client = self.ws_clients.get(key)
            if client is None:
                token_for_client = token
                client = JX3WSClient(
                    url=url,
                    token=token_for_client,
                    on_message=lambda raw, token_key=key: self.handle_ws_message(raw, token_key),
                )
                self.ws_clients[key] = client
            else:
                token_for_client = token
            await client.configure(token_for_client, bool(actions))

    async def init_tasks(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("后台监控调度器已启动")
        await self.refresh_jobs()
        if self.scheduler.get_job("credential_pool_recheck") is None:
            self.scheduler.add_job(
                self._credential_pool_recheck,
                IntervalTrigger(hours=24),
                id="credential_pool_recheck",
                max_instances=1,
            )

    async def refresh_jobs(self):
        enabled = set(await self.sessions.enabled_push_actions())
        for action, meta in self.jobs.items():
            job_id = f"push_{action}"
            running = self.scheduler.get_job(job_id) is not None
            if action in enabled and not running:
                self._add_scheduler(action, meta["name"], meta["interval"])
            elif action not in enabled and running:
                self.scheduler.remove_job(job_id)
                logger.info(f"{meta['name']}后台任务已停止")
        event_actions = enabled - set(self.jobs)
        groups = await self._push_token_groups(event_actions)
        await self._configure_ws_clients(groups)

    def _add_scheduler(self, action: str, name: str, interval: int):
        job_id = f"push_{action}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        self.scheduler.add_job(
            func=self._job,
            trigger=IntervalTrigger(seconds=interval),
            id=job_id,
            args=[action, name],
        )
        logger.info(f"{name}后台任务启动成功，周期：{interval}s")

    async def _credential_pool_recheck(self):
        try:
            from .credential_runtime import restore_recoverable_tokens

            restored = await restore_recoverable_tokens(self.jx3api, self.sessions)
            if restored:
                logger.info(f"已恢复 {len(restored)} 枚移除池接口令牌")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("移除池接口令牌每日检查失败")

    async def _job(self, action: str, name: str):
        try:
            enabled = await self.sessions.enabled_push_actions()
            if action not in enabled:
                job_id = f"push_{action}"
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                return
            servers = await self.sessions.servers_with_push(action)
            for server in servers:
                await self._push_server(action, server)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"{name} 后台任务执行异常")

    async def handle_ws_message(self, raw, token_key: str = "__scheduled__"):
        parsed = parse_ws_message(raw)
        action = parsed.get("action") or 0
        payload = parsed.get("payload") or {}
        action_id = resolve_push_action(action)
        if not action_id:
            return
        text = format_event_text(action, payload)
        if not text:
            return
        server = str(payload.get("server") or "").strip()
        resolver = getattr(self.sessions, "resolve_server", None)
        if callable(resolver):
            official = resolver(server)
            if official:
                server = official
        status = event_dedupe_key(action, payload)
        if action_id != "0":
            legacy = await self.sessions.get_push_state(action_id, server or "*", "__scheduled__")
            if legacy == status:
                targets = await self.sessions.push_targets(action_id, server)
                targets = await self._targets_for_token(targets, token_key, action_id)
                if targets:
                    await self.sessions.set_push_state(action_id, server or "*", status, token_key)
                return
        old = await self.sessions.get_push_state(action_id, server or "*", token_key)
        if old == status:
            return
        targets = await self.sessions.push_targets(action_id, server)
        targets = await self._targets_for_token(targets, token_key, action_id)
        if not targets:
            return
        await self._send(targets, text, action_id)
        await self.sessions.set_push_state(action_id, server or "*", status, token_key)

    async def _targets_for_token(self, targets: list[dict], token_key: str, action: str = ""):
        if token_key == "__scheduled__":
            return targets
        if token_key == "__free__" and action not in FREE_PUSH_ACTIONS:
            return []
        global_push_token = self._ws_token()
        matched = []
        for row in targets:
            token = self.sessions.resolve_push_token(row, global_push_token)
            row_key = self._token_key("" if token == CREDENTIAL_MISSING else token)
            if row_key == token_key:
                matched.append(row)
        return matched

    async def _push_server(self, action: str, server: str):
        data = await self.jx3box.machangxiaoxi(server, "chitu-horse", "share_msg")
        if not isinstance(data, dict):
            return
        if data.get("code") != 200:
            logger.warning(f"赤兔轮询上游失败，保留上次状态: server={server}, error={data.get('msg')}")
            return
        status = event_dedupe_key(
            action,
            {"status": data.get("status"), "data": data.get("data")},
        )
        old = await self.sessions.get_push_state(action, server)
        if old == status:
            return
        targets = await self.sessions.push_targets(action, server)
        text = data.get("data") or ""
        if not text:
            return
        await self._send(targets, data.get("data") or "", action)
        await self.sessions.set_push_state(action, server, status)

    async def _send(self, targets, text: str, action: str):
        if not text or not targets:
            return
        message_chain = MessageChain().message(text)
        for row in targets:
            umo = row.get("umo")
            if not umo:
                continue
            async with self.sessions.session_lock(umo):
                if not await self.sessions.is_active_push_target(umo, action):
                    continue
                try:
                    sent = await self.context.send_message(umo, message_chain)
                except Exception as exc:
                    logger.warning(f"主动推送发送失败: {umo}, error={exc}")
                    if is_permanent_group_failure(exc):
                        await self.sessions.record_permanent_push_failure(umo, str(exc))
                else:
                    if sent:
                        await self.sessions.mark_push_success(umo)
                    else:
                        logger.warning(f"主动推送平台不可达，已跳过计数: {umo}")

    def stop_all_tasks(self):
        try:
            self.scheduler.remove_all_jobs()
            logger.info("已停止全部后台任务")
        except Exception as e:
            logger.error(f"停止全部后台任务失败：{e}")

    async def destroy(self):
        try:
            for client in list(self.ws_clients.values()):
                await client.stop()
            self.ws_clients.clear()
            self.stop_all_tasks()
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            logger.info("后台调度器已销毁")
        except Exception as e:
            logger.error(f"销毁调度器失败：{e}")
