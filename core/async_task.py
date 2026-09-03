# pyright: reportArgumentType=false
import asyncio
import hashlib
from functools import partial
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from astrbot.api.event import MessageChain
from astrbot.api.star import Context
from astrbot.api import logger
from astrbot.api import AstrBotConfig

from .event_catalog import (
    ACTION_IDS,
    FREE_PUSH_ACTIONS,
    event_dedupe_key,
    format_event_text,
    parse_ws_message,
    resolve_push_action,
)
from .jx3api_data import JX3APIService
from .jx3box_data import CHITU_NO_EVENT_MESSAGE, JX3BOXService
from .push_errors import is_permanent_group_failure
from .session_store import SessionStore
from .ws_client import DEFAULT_WS_URL, JX3WSClient


SEND_TIMEOUT_SECONDS = 15
PUSH_RETRY_INTERVAL_SECONDS = 5
PUSH_RETRY_WINDOW_SECONDS = 60
CLOCK_SKEW_SECONDS = 5
PUSH_EVENT_QUEUE_MAXSIZE = 1000
PUSH_RETRY_TEXT_MAX_CHARS = 500


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
            "0": {"interval": 20, "name": "赤兔消息"},
        }
        self.ws_clients: dict[str, JX3WSClient] = {}
        self._push_token_options: dict[str, list[str]] = {}
        self._ensure_runtime_state()
        logger.info("初始化推送功能成功")

    @staticmethod
    def _token_key(token: str) -> str:
        token = (token or "").strip()
        if not token:
            return "__free__"
        return "token:" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]

    def _ensure_runtime_state(self):
        if not hasattr(self, "_refresh_lock"):
            self._refresh_lock = asyncio.Lock()
        if not hasattr(self, "_event_claims"):
            self._event_claims = set()
        if not hasattr(self, "_event_claims_lock"):
            self._event_claims_lock = asyncio.Lock()
        if not hasattr(self, "_event_queue"):
            self._event_queue = asyncio.Queue(maxsize=PUSH_EVENT_QUEUE_MAXSIZE)
        if not hasattr(self, "_event_worker_task"):
            self._event_worker_task = None
        if not hasattr(self, "_retry_tasks"):
            self._retry_tasks = set()
        if not hasattr(self, "_retry_tasks_by_umo"):
            self._retry_tasks_by_umo = {}

    @staticmethod
    def _event_time(payload: dict) -> datetime:
        keys = (
            "event_time", "time", "timestamp", "created_at", "created",
            "capture_time", "auction_time", "start_time", "end_time",
        )
        raw = next((payload.get(key) for key in keys if payload.get(key) not in (None, "")), None)
        now = datetime.now(timezone.utc)
        event_time: datetime | None = None
        try:
            if isinstance(raw, (int, float)) or (isinstance(raw, str) and str(raw).strip().isdigit()):
                seconds = float(raw)
                if seconds > 10_000_000_000:
                    seconds /= 1000
                event_time = datetime.fromtimestamp(seconds, tz=timezone.utc)
            text = str(raw or "").strip()
            if text:
                event_time = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
        except (TypeError, ValueError, OverflowError, OSError):
            pass
        if event_time is None:
            return now
        if event_time > now + timedelta(seconds=CLOCK_SKEW_SECONDS):
            return now
        return event_time.astimezone(timezone.utc)

    async def _push_token_groups(
        self,
        event_actions: set[str],
        status_cache: dict[str, tuple[str, str]] | None = None,
    ) -> dict[str, dict[str, set[str] | str]]:
        credential_actions = event_actions - FREE_PUSH_ACTIONS
        rows_by_action = await self._prepare_push_assignments(
            event_actions, credential_actions, status_cache=status_cache
        )
        groups: dict[str, dict[str, set[str] | str]] = {}
        for action in event_actions:
            for row in rows_by_action[action]:
                umo = str(row.get("umo") or "")
                if action in FREE_PUSH_ACTIONS:
                    key = self._token_key("")
                    group = groups.setdefault(key, {"actions": set(), "token": ""})
                    cast_set = group["actions"]
                    cast_set.add(action)
                else:
                    options = self._push_token_options.get(umo, [])
                    for token in options:
                        key = self._token_key(token)
                        group = groups.setdefault(key, {"actions": set(), "token": token})
                        cast_set = group["actions"]
                        cast_set.add(action)
        return groups

    async def _prepare_push_assignments(
        self,
        event_actions: set[str],
        credential_actions: set[str] | None = None,
        status_cache: dict[str, tuple[str, str]] | None = None,
    ) -> dict[str, list[dict]]:
        rows_by_action: dict[str, list[dict]] = {}
        unique_rows: dict[str, dict] = {}
        for action in event_actions:
            targets = await self.sessions.rows_with_push_action(action)
            rows_by_action[action] = targets
            for row in targets:
                umo = str(row.get("umo") or "")
                if umo:
                    unique_rows[umo] = row

        credential_actions = event_actions if credential_actions is None else credential_actions
        status_cache = status_cache if status_cache is not None else {}
        credential_rows = {
            str(row.get("umo") or ""): row
            for action in credential_actions
            for row in rows_by_action.get(action, [])
            if str(row.get("umo") or "")
        }
        token_values_by_umo: dict[str, list[str]] = {}
        token_owners: dict[str, list[tuple[str, str]]] = {}
        for umo, row in credential_rows.items():
            source, values = await self.sessions.resolve_credential_pool(umo, "push_token")
            token_values_by_umo[umo] = list(values)
            for value in values:
                token_owners.setdefault(value, []).append((source, umo))

        token_states = dict(zip(
            token_owners.keys(),
            await asyncio.gather(
                *(
                    self._inspect_push_token(value, status_cache)
                    for value in token_owners.keys()
                )
            ),
        ))
        for value, (state, reason) in token_states.items():
            if state != "failed":
                continue
            for source, umo in token_owners[value]:
                if source == "group":
                    await self.sessions.remove_pool_credential(umo, "push_token", value, reason)
                elif source == "global":
                    await self.sessions.remove_global_credential("push_token", value, reason)

        next_options: dict[str, list[str]] = {}
        for umo, values in token_values_by_umo.items():
            next_options[umo] = [
                value for value in values if token_states[value][0] != "failed"
            ]
        self._push_token_options = next_options
        return rows_by_action

    async def _inspect_push_token(
        self,
        value: str,
        status_cache: dict[str, tuple[str, str]],
    ) -> tuple[str, str]:
        value = str(value or "").strip()
        if not value:
            return "failed", "推送令牌为空"
        if value not in status_cache:
            from .credentials import inspect_token_status

            state, reason, _remaining = await inspect_token_status(self.jx3api, value)
            status_cache[value] = (state, reason)
        return status_cache[value]

    async def _configure_ws_clients(self, groups: dict[str, dict[str, set[str] | str]]) -> None:
        url = str(self.conf.get("jx3api_ws_url", "") or DEFAULT_WS_URL)
        for key in list(self.ws_clients):
            if key not in groups:
                await self.ws_clients.pop(key).stop()
        for key, group in groups.items():
            token = str(group["token"] or "")
            client = self.ws_clients.get(key)
            if client is None:
                token_for_client = token
                client = JX3WSClient(
                    url=url,
                    token=token_for_client,
                    on_message=lambda raw, token_key=key: self._enqueue_ws_message(raw, token_key),
                )
                self.ws_clients[key] = client
            else:
                token_for_client = token
            await client.configure(
                token_for_client,
                True,
                url,
            )

    async def init_tasks(self):
        self._ensure_runtime_state()
        self._start_event_worker()
        await self._restore_push_retries()
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
        self._ensure_runtime_state()
        async with self._refresh_lock:
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
            status_cache: dict[str, tuple[str, str]] = {}
            groups = await self._push_token_groups(event_actions, status_cache=status_cache)
            for key, group in (
                await self._push_token_connection_groups(status_cache=status_cache)
            ).items():
                groups.setdefault(key, group)
            free_key = self._token_key("")
            groups.setdefault(free_key, {"actions": set(), "token": ""})
            await self._configure_ws_clients(groups)

    async def _push_token_connection_groups(
        self,
        status_cache: dict[str, tuple[str, str]] | None = None,
    ) -> dict[str, dict[str, set[str] | str]]:
        groups: dict[str, dict[str, set[str] | str]] = {}
        status_cache = status_cache if status_cache is not None else {}

        global_values = await self.sessions.list_active_global_credentials("push_token")
        token_owners: dict[str, list[tuple[str, str]]] = {
            value: [("global", "")] for value in global_values
        }
        for row in await self.sessions.list_all():
            umo = str(row.get("umo") or "")
            if not umo:
                continue
            for value in await self.sessions.list_active_credentials(umo, "push_token"):
                token_owners.setdefault(value, []).append(("group", umo))

        token_states = dict(zip(
            token_owners.keys(),
            await asyncio.gather(
                *(
                    self._inspect_push_token(value, status_cache)
                    for value in token_owners.keys()
                )
            ),
        ))
        for value, (state, reason) in token_states.items():
            if state == "failed":
                for source, owner in token_owners[value]:
                    if source == "group":
                        await self.sessions.remove_pool_credential(
                            owner, "push_token", value, reason
                        )
                    elif source == "global":
                        await self.sessions.remove_global_credential(
                            "push_token", value, reason
                        )
                continue
            key = self._token_key(value)
            groups.setdefault(key, {"actions": set(), "token": value})

        return groups

    def _start_event_worker(self):
        self._ensure_runtime_state()
        if self._event_worker_task and not self._event_worker_task.done():
            return
        self._event_worker_task = asyncio.create_task(
            self._event_worker(),
            name="jx3-push-event-worker",
        )

    async def _enqueue_ws_message(self, raw, token_key: str = "__scheduled__"):
        self._ensure_runtime_state()
        await self._event_queue.put((raw, token_key))

    async def _event_worker(self):
        while True:
            raw, token_key = await self._event_queue.get()
            try:
                await self.handle_ws_message(raw, token_key)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("主动推送事件处理失败")
            finally:
                self._event_queue.task_done()

    async def _release_event_claim(self, claim_key: str):
        async with self._event_claims_lock:
            self._event_claims.discard(claim_key)

    async def _schedule_retry(
        self,
        row: dict,
        text: str,
        action: str,
        server: str,
        status: str,
        state_key: str,
        event_time: datetime,
        claim_key: str,
        persist: bool = True,
    ) -> bool:
        self._ensure_runtime_state()
        if persist:
            try:
                await self.sessions.add_push_retry(
                    claim_key=claim_key,
                    action=action,
                    server=server or "*",
                    umo=str(row.get("umo") or ""),
                    status=status,
                    text=text,
                    state_key=state_key,
                    event_time=event_time.isoformat(),
                )
            except Exception:
                logger.exception("主动推送补推队列写入失败")
                # The in-memory retry still covers this 60-second window; do not
                # mark the target consumed just because the queue write failed.
                persist = False
        try:
            task = asyncio.create_task(
                self._retry_delivery(
                    row, text, action, server, status, state_key, event_time, claim_key
                ),
                name="jx3-push-retry",
            )
        except RuntimeError:
            return False
        self._retry_tasks.add(task)
        self._retry_tasks_by_umo.setdefault(str(row.get("umo") or ""), set()).add(task)
        task.add_done_callback(self._retry_tasks.discard)
        task.add_done_callback(partial(self._discard_retry_task_by_umo, str(row.get("umo") or "")))
        return True

    def _discard_retry_task_by_umo(self, umo: str, task: asyncio.Task):
        tasks = self._retry_tasks_by_umo.get(umo)
        if tasks:
            tasks.discard(task)
            if not tasks:
                self._retry_tasks_by_umo.pop(umo, None)

    async def cancel_push_retries_for_umo(self, umo: str):
        tasks = list(self._retry_tasks_by_umo.get(str(umo or ""), set()))
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _restore_push_retries(self):
        self._ensure_runtime_state()
        for record in await self.sessions.list_push_retry():
            claim_key = str(record.get("claim_key") or "")
            action = str(record.get("action") or "")
            server = str(record.get("server") or "*")
            state_key = str(record.get("state_key") or "")
            status = str(record.get("status") or "")
            if action in ACTION_IDS:
                existing_state = await self.sessions.get_push_state(action, server, state_key)
                if existing_state == status:
                    await self.sessions.delete_push_retry(claim_key)
                    continue
            try:
                event_time = datetime.fromisoformat(
                    str(record.get("event_time") or "").replace("Z", "+00:00")
                )
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if event_time > now + timedelta(seconds=CLOCK_SKEW_SECONDS):
                    event_time = now
            except (TypeError, ValueError):
                logger.warning("主动推送补推记录时间无效，已丢弃")
                await self.sessions.delete_push_retry(claim_key)
                continue
            if not claim_key or claim_key in self._event_claims:
                continue
            self._event_claims.add(claim_key)
            scheduled = await self._schedule_retry(
                {"umo": str(record.get("umo") or "")},
                str(record.get("text") or ""),
                action,
                server,
                status,
                state_key,
                event_time,
                claim_key,
                persist=False,
            )
            if not scheduled:
                await self._release_event_claim(claim_key)

    async def _finish_retry(
        self,
        row: dict,
        action: str,
        server: str,
        status: str,
        claim_key: str,
        mark_umos: set[str],
    ):
        umo = str(row.get("umo") or "")
        if await self.sessions.is_active_push_target(umo, action):
            await self._mark_push_states([row], action, server, status, mark_umos)
        try:
            await self.sessions.delete_push_retry(claim_key)
        except Exception:
            logger.exception("主动推送补推队列清理失败")
        await self._release_event_claim(claim_key)

    async def _retry_delivery(
        self,
        row: dict,
        text: str,
        action: str,
        server: str,
        status: str,
        state_key: str,
        event_time: datetime,
        claim_key: str,
    ):
        try:
            deadline = event_time + timedelta(seconds=PUSH_RETRY_WINDOW_SECONDS)
            while True:
                remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
                if remaining <= 0:
                    break
                await asyncio.sleep(min(PUSH_RETRY_INTERVAL_SECONDS, remaining))
                sent_umos, retryable_umos = await self._send([row], text, action)
                if row.get("umo") in sent_umos:
                    await self._finish_retry(
                        row,
                        action,
                        server,
                        status,
                        claim_key,
                        {str(row.get("umo") or "")},
                    )
                    return
                if str(row.get("umo") or "") not in retryable_umos:
                    await self._finish_retry(
                        row,
                        action,
                        server,
                        status,
                        claim_key,
                        {str(row.get("umo") or "")},
                    )
                    return
            await self._finish_retry(
                row,
                action,
                server,
                status,
                claim_key,
                {str(row.get("umo") or "")},
            )
        finally:
            await self._release_event_claim(claim_key)

    async def _mark_push_states(
        self,
        rows: list[dict],
        action: str,
        server: str,
        status: str,
        mark_umos: set[str] | None = None,
    ):
        async with self.sessions._push_state_lock:
            for row in rows:
                umo = str(row.get("umo") or "")
                if mark_umos is not None and umo not in mark_umos:
                    continue
                await self.sessions.set_push_state_locked(
                    action,
                    server or "*",
                    status,
                    f"umo:{umo}",
                )

    async def _deliver_pending(
        self,
        rows: list[dict],
        text: str,
        action: str,
        server: str,
        status: str,
        event_time: datetime,
    ):
        self._ensure_runtime_state()
        state_keys: dict[str, str] = {}
        claim_prefix = f"{action}:{server or '*'}:{status}"
        acquired: list[tuple[dict, str]] = []
        async with self._event_claims_lock:
            for row in rows:
                umo = str(row.get("umo") or "")
                state_keys[umo] = f"umo:{umo}"
                claim_key = f"{claim_prefix}:{umo}"
                if claim_key in self._event_claims:
                    continue
                self._event_claims.add(claim_key)
                acquired.append((row, claim_key))
        if not acquired:
            return

        retry_claim_keys: set[str] = set()
        try:
            sent_umos, retryable_umos = await self._send(
                [row for row, _claim in acquired], text, action
            )
            for row, claim_key in acquired:
                umo = str(row.get("umo") or "")
                if umo in sent_umos:
                    await self._mark_push_states(
                        [row], action, server, status, {umo}
                    )
                    await self._release_event_claim(claim_key)
                elif umo in retryable_umos:
                    scheduled = await self._schedule_retry(
                        row,
                        text,
                        action,
                        server or "*",
                        status,
                        state_keys[umo],
                        event_time,
                        claim_key,
                    )
                    if scheduled:
                        retry_claim_keys.add(claim_key)
                    else:
                        await self._mark_push_states(
                            [row], action, server, status, {umo}
                        )
                        await self._release_event_claim(claim_key)
                else:
                    await self._mark_push_states(
                        [row], action, server, status, {umo}
                    )
                    await self._release_event_claim(claim_key)
        finally:
            for row, claim_key in acquired:
                if claim_key not in retry_claim_keys:
                    await self._release_event_claim(claim_key)

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
                logger.info(f"已恢复 {len(restored)} 枚失效池令牌")
                await self.refresh_jobs()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("失效池令牌每日检查失败")

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
        self._ensure_runtime_state()
        parsed = parse_ws_message(raw)
        action = parsed.get("action") or 0
        payload = parsed.get("payload") or {}
        action_id = resolve_push_action(action)
        if not action_id:
            return
        if action_id == "0":
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
        event_time = self._event_time(payload)
        event_age = (datetime.now(timezone.utc) - event_time).total_seconds()
        if event_age > PUSH_RETRY_WINDOW_SECONDS:
            return
        targets = await self.sessions.push_targets(action_id, server)
        targets = await self._targets_for_token(targets, token_key, action_id)
        if not targets:
            return
        pending = []
        state_keys: dict[str, str] = {}
        for row in targets:
            umo = str(row.get("umo") or "")
            state_key = f"umo:{umo}"
            state_keys[umo] = state_key
            old = await self.sessions.get_push_state(action_id, server or "*", state_key)
            if old != status:
                pending.append(row)
        if not pending:
            return

        await self._deliver_pending(
            pending, text, action_id, server, status, event_time
        )

    async def _targets_for_token(self, targets: list[dict], token_key: str, action: str = ""):
        if token_key == "__scheduled__":
            return targets
        is_free_connection = token_key == "__free__"
        if is_free_connection != (action in FREE_PUSH_ACTIONS):
            return []
        if is_free_connection:
            return targets
        matched = []
        for row in targets:
            if token_key in [
                self._token_key(token)
                for token in self._push_token_options.get(str(row.get("umo") or ""), [])
            ]:
                matched.append(row)
        return matched

    async def _push_server(self, action: str, server: str):
        self._ensure_runtime_state()
        data = await self.jx3box.machangxiaoxi(server)
        if not isinstance(data, dict):
            return
        if data.get("code") != 200:
            if data.get("msg") == CHITU_NO_EVENT_MESSAGE:
                return
            logger.warning(f"赤兔轮询上游失败，保留上次状态: server={server}, error={data.get('msg')}")
            return
        status = event_dedupe_key(
            action,
            {"status": data.get("status"), "data": data.get("data")},
        )
        targets = await self.sessions.push_targets(action, server)
        text = data.get("data") or ""
        if not text:
            return
        pending = []
        state_keys: dict[str, str] = {}
        for row in targets:
            umo = str(row.get("umo") or "")
            state_keys[umo] = f"umo:{umo}"
            old = await self.sessions.get_push_state(action, server, state_keys[umo])
            if old != status:
                pending.append(row)
        await self._deliver_pending(
            pending,
            data.get("data") or "",
            action,
            server,
            status,
            self._event_time(data),
        )

    async def _send(self, targets, text: str, action: str):
        if not text or not targets:
            return set(), set()
        message_chain = MessageChain().message(text)
        sent_umos: set[str] = set()
        retryable_umos: set[str] = set()
        results = await asyncio.gather(
            *(self._send_one(row, message_chain, action) for row in targets),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, BaseException):
                continue
            delivered, retryable = result
            if delivered:
                sent_umos.add(delivered)
            if retryable:
                retryable_umos.add(retryable)
        return sent_umos, retryable_umos

    async def _send_one(self, row: dict, message_chain, action: str) -> tuple[str | None, str | None]:
        umo = str(row.get("umo") or "")
        if not umo:
            return None, None
        if action not in FREE_PUSH_ACTIONS:
            _source, values = await self.sessions.resolve_credential_pool(umo, "push_token")
            if not values:
                logger.warning(f"主动推送缺少可用推送令牌，已跳过: {umo}")
                return None, None
        try:
            async with self.sessions.session_lock(umo):
                if not await self.sessions.is_active_push_target(umo, action):
                    return None, None
                try:
                    sent = await asyncio.wait_for(
                        self.context.send_message(umo, message_chain),
                        timeout=SEND_TIMEOUT_SECONDS,
                    )
                except Exception as exc:
                    logger.warning(f"主动推送发送失败: {umo}, error={exc}")
                    if is_permanent_group_failure(exc):
                        await self.sessions.record_permanent_push_failure(umo, str(exc))
                        return None, None
                    return None, umo
                else:
                    if sent:
                        await self.sessions.mark_push_success(umo)
                        return umo, None
                    logger.warning(f"主动推送平台不可达，已跳过计数: {umo}")
                    return None, umo
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(f"主动推送目标处理失败: {umo}, error={exc}")
            return None, umo

    async def _cancel_runtime_tasks(self):
        tasks = list(self._retry_tasks)
        if self._event_worker_task:
            tasks.append(self._event_worker_task)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def stop_all_tasks(self):
        try:
            self.scheduler.remove_all_jobs()
            logger.info("已停止全部后台任务")
        except Exception as e:
            logger.error(f"停止全部后台任务失败：{e}")

    async def destroy(self):
        try:
            await self._cancel_runtime_tasks()
            for client in list(self.ws_clients.values()):
                await client.stop()
            self.ws_clients.clear()
            self.stop_all_tasks()
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            logger.info("后台调度器已销毁")
        except Exception as e:
            logger.error(f"销毁调度器失败：{e}")
