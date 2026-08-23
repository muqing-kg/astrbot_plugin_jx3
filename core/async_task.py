# pyright: reportArgumentType=false
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from astrbot.api.event import MessageChain
from astrbot.api.star import Context
from astrbot.api import logger
from astrbot.api import AstrBotConfig

from .jx3api_data import JX3APIService
from .jx3box_data import JX3BOXService
from .session_store import SessionStore


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
            "开服": {"interval": 60, "name": "开服监控"},
            "新闻": {"interval": 280, "name": "新闻资讯"},
            "刷马": {"interval": 60, "name": "刷马消息"},
            "赤兔": {"interval": 60, "name": "赤兔消息"},
        }
        logger.info("初始化推送功能成功")

    async def init_tasks(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("后台监控调度器已启动")
        await self.refresh_jobs()

    async def refresh_jobs(self):
        enabled = set(await self.sessions.enabled_push_kinds())
        for kind, meta in self.jobs.items():
            job_id = f"push_{kind}"
            running = self.scheduler.get_job(job_id) is not None
            if kind in enabled and not running:
                self._add_scheduler(kind, meta["name"], meta["interval"])
            elif kind not in enabled and running:
                self.scheduler.remove_job(job_id)
                logger.info(f"{meta['name']}后台任务已停止")

    def _add_scheduler(self, kind: str, name: str, interval: int):
        job_id = f"push_{kind}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        self.scheduler.add_job(
            func=self._job,
            trigger=IntervalTrigger(seconds=interval),
            id=job_id,
            args=[kind, name],
        )
        logger.info(f"{name}后台任务启动成功，周期：{interval}s")

    async def _job(self, kind: str, name: str):
        try:
            enabled = await self.sessions.enabled_push_kinds()
            if kind not in enabled:
                job_id = f"push_{kind}"
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                return
            if kind == "新闻":
                await self._push_news()
                return
            servers = await self.sessions.servers_with_push(kind)
            for server in servers:
                await self._push_server(kind, server)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(f"{name} 后台任务执行异常")

    async def _push_news(self):
        data = await self.jx3api.xinwen(1)
        if not isinstance(data, dict):
            return
        status = str(data.get("status"))
        old = await self.sessions.get_push_state("新闻", "*")
        if old == status:
            return
        targets = await self.sessions.push_targets("新闻")
        await self._send(targets, data.get("data") or "")
        await self.sessions.set_push_state("新闻", "*", status)

    async def _push_server(self, kind: str, server: str):
        if kind == "开服":
            data = await self.jx3api.kaifu(server)
        elif kind == "刷马":
            data = await self.jx3box.machangxiaoxi(server, "horse", "foreshow")
        else:
            data = await self.jx3box.machangxiaoxi(server, "chitu-horse", "share_msg")
        if not isinstance(data, dict):
            return
        status = str(data.get("status"))
        old = await self.sessions.get_push_state(kind, server)
        if old == status:
            return
        targets = await self.sessions.push_targets(kind, server)
        await self._send(targets, data.get("data") or "")
        await self.sessions.set_push_state(kind, server, status)

    async def _send(self, targets, text: str):
        if not text or not targets:
            return
        message_chain = MessageChain().message(text)
        for row in targets:
            umo = row.get("umo")
            if not umo:
                continue
            await self.context.send_message(umo, message_chain)

    def stop_all_tasks(self):
        try:
            self.scheduler.remove_all_jobs()
            logger.info("已停止全部后台任务")
        except Exception as e:
            logger.error(f"停止全部后台任务失败：{e}")

    async def destroy(self):
        try:
            self.stop_all_tasks()
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            logger.info("后台调度器已销毁")
        except Exception as e:
            logger.error(f"销毁调度器失败：{e}")
