from __future__ import annotations

import itertools
import logging
import threading
from collections import deque
from datetime import datetime
from typing import Any

from astrbot.api import logger as astrbot_logger


LOG_BUFFER_SIZE = 1000
LOG_MESSAGE_MAX_CHARS = 4000

_LOGGER_NAME = "astrbot_plugin_jx3"
_logger = logging.getLogger(_LOGGER_NAME)
_logger.setLevel(logging.DEBUG)
_logger.propagate = False

def configure_plugin_logger():
    """Idempotently install plugin handlers and remove stale duplicates."""
    global _memory_handler, _forward_handler
    _memory_handler = next(
        (handler for handler in _logger.handlers if isinstance(handler, MemoryLogHandler)),
        MemoryLogHandler(),
    )
    _forward_handler = next(
        (handler for handler in _logger.handlers if isinstance(handler, AstrBotForwardHandler)),
        AstrBotForwardHandler(astrbot_logger),
    )
    deduped = []
    for handler in _logger.handlers:
        if not isinstance(handler, (MemoryLogHandler, AstrBotForwardHandler)):
            deduped.append(handler)
    if not any(isinstance(handler, MemoryLogHandler) for handler in deduped):
        deduped.append(_memory_handler)
    if not any(isinstance(handler, AstrBotForwardHandler) for handler in deduped):
        deduped.append(_forward_handler)
    _logger.handlers = deduped


def _source_for_record(record: logging.LogRecord) -> str:
    explicit = getattr(record, "log_source", "")
    if explicit:
        return str(explicit)
    module = str(record.module or "").lower()
    if module == "ws_client":
        return "websocket"
    if module == "request":
        return "query"
    if module == "page_api":
        return "webui"
    if module in {"jx3api_data", "jx3box_data", "aijx3_data", "unua_data", "yymj_data"}:
        return "query"
    if module == "message":
        return "query"
    if module == "credential_runtime":
        return "query"
    if module == "async_task":
        message = record.getMessage()
        if "补推" in message:
            return "retry"
        if "赤兔" in message:
            return "chitu"
        return "event"
    return "plugin"


class MemoryLogHandler(logging.Handler):
    def __init__(self, capacity: int = LOG_BUFFER_SIZE):
        super().__init__(level=logging.DEBUG)
        self.capacity = capacity
        self._records: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._lock = threading.RLock()
        self._ids = itertools.count(1)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            if record.exc_info:
                message += "\n" + self.format(record)
            with self._lock:
                entry = {
                    "id": next(self._ids),
                    "time": datetime.now().astimezone().isoformat(timespec="milliseconds"),
                    "level": record.levelname,
                    "source": _source_for_record(record),
                    "message": message[:LOG_MESSAGE_MAX_CHARS],
                    "umo": str(getattr(record, "log_umo", "") or ""),
                    "action": str(getattr(record, "log_action", "") or ""),
                    "server": str(getattr(record, "log_server", "") or ""),
                }
                self._records.append(entry)
        except Exception:
            self.handleError(record)

    def snapshot(
        self,
        *,
        limit: int = 300,
        level: str = "",
        source: str = "",
        keyword: str = "",
        after_id: int = 0,
    ) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._records)

        level_name = str(level or "").upper()
        keyword = str(keyword or "").lower()
        result = []
        for row in records:
            if after_id and row["id"] <= after_id:
                continue
            if level_name and row["level"] != level_name:
                continue
            if source and row["source"] != source:
                continue
            if keyword and keyword not in row["message"].lower():
                continue
            result.append(row)
        if limit > 0:
            result = result[-limit:]
        return result

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


class AstrBotForwardHandler(logging.Handler):
    def __init__(self, target):
        super().__init__(level=logging.WARNING)
        self.target = target

    def emit(self, record: logging.LogRecord) -> None:
        method = {
            logging.WARNING: "warning",
            logging.ERROR: "error",
            logging.CRITICAL: "error",
        }.get(record.levelno, "info")
        callback = getattr(self.target, method, None)
        if callback:
            try:
                callback(record.getMessage(), exc_info=record.exc_info)
            except Exception:
                self.handleError(record)


configure_plugin_logger()

logger = _logger
memory_handler = _memory_handler
