from contextvars import ContextVar
import re
from typing import Any

from .session_policy import mask_for_user

_request_token: ContextVar[str | None] = ContextVar("jx3_request_token", default=None)
_request_ticket: ContextVar[str | None] = ContextVar("jx3_request_ticket", default=None)


class CredentialRuntimeError(RuntimeError):
    def __init__(self, kind: str, reason: str):
        self.kind = kind
        self.reason = reason
        super().__init__(reason)


def set_request_credentials(token: str | None, ticket: str | None):
    token_token = _request_token.set(token)
    ticket_token = _request_ticket.set(ticket)
    return token_token, ticket_token


def reset_request_credentials(tokens) -> None:
    if not tokens:
        return
    _request_token.reset(tokens[0])
    _request_ticket.reset(tokens[1])


def current_token(fallback: str = "") -> str:
    value = _request_token.get()
    if value is not None:
        return value
    return fallback or ""


def current_ticket(fallback: str = "") -> str:
    value = _request_ticket.get()
    if value is not None:
        return value
    return fallback or ""


TOKEN_ERROR_PATTERN = re.compile(
    r"(?:"
    r"\btoken\b[^\n]*(?:invalid|expired|not found|does not exist|unavailable|quota|balance)"
    r"|(?:invalid|expired|not found|does not exist|unavailable)[^\n]*\btoken\b"
    r"|remaining(?:\s+token)?(?:\s+count)?\s*(?:is\s*)?0"
    r"|令牌[^\n]*(?:无效|失效|过期|不存在|不可用|次数不足|额度不足|额度用尽|余额不足|剩余为\s*0)"
    r"|(?:无效|失效|过期|不存在|不可用)[^\n]*令牌"
    r"|剩余(?:次数|额度|余额)(?:不足|为\s*0|已用尽)"
    r"|(?:次数|额度|余额)(?:已用尽|不足)"
    r")",
    re.IGNORECASE,
)

TICKET_ERROR_PATTERN = re.compile(
    r"(?:"
    r"\bticket\b[^\n]*(?:invalid|expired|not found|does not exist|unavailable|quota|balance)"
    r"|(?:invalid|expired|not found|does not exist|unavailable)[^\n]*\bticket\b"
    r"|推栏(?:标识)?[^\n]*(?:无效|失效|过期|不存在|不可用|次数不足|额度不足|额度用尽|余额不足)"
    r"|(?:无效|失效|过期|不存在|不可用)[^\n]*推栏(?:标识)?"
    r")",
    re.IGNORECASE,
)


def credential_failure(raw: Any, code: Any = None) -> tuple[str, str] | None:
    """Classify explicit JX3API credential failures only."""
    text = str(raw or "").strip()
    if not text:
        if code in (401, 403):
            return "token", f"HTTP {code}"
        return None
    if TICKET_ERROR_PATTERN.search(text):
        return "ticket", text
    if TOKEN_ERROR_PATTERN.search(text):
        return "token", text
    if code in (401, 403):
        return "token", text
    return None


def credential_message(kind: str, raw: Any) -> str:
    text = str(raw or "").strip()
    if kind == "ticket":
        if "过期" in text or "expire" in text.lower():
            return "推栏标识已失效。"
        if "token" in text.lower() or "令牌" in text:
            return "推栏标识校验失败。"
        return text or "推栏标识不可用。"
    if "expire" in text.lower() or "过期" in text:
        return "接口令牌已过期。"
    if "quota" in text.lower() or "剩余" in text:
        return "接口令牌次数不足。"
    if any(key in text for key in ("次数", "余额", "额度", "用尽", "不足")):
        return "接口令牌次数不足。"
    return text or "接口令牌不可用。"


async def validate_pool_token(jx3api, value: str) -> tuple[bool, str, int | None]:
    """Validate one interface token for the group-owned pool."""
    result = await jx3api.token_stats(value)
    if result.get("code") != 200 or result.get("valid") is False:
        detail = str(result.get("msg") or "接口令牌不可用")
        return False, jx3api._token_error_message(detail), None
    detail = result.get("detail") if isinstance(result.get("detail"), dict) else {}
    remaining = detail.get("remaining")
    if remaining is None:
        return True, "", None
    try:
        remaining = int(remaining)
    except (TypeError, ValueError):
        return True, "", None
    if remaining < 100:
        return False, "接口令牌剩余次数少于 100。", remaining
    return True, "", remaining

async def inspect_token_status(
    jx3api,
    value: str,
) -> tuple[str, str, int | None]:
    """Return token state as ok/failed/unknown with a readable reason."""
    result = await jx3api.token_stats(value)
    if result.get("_transport_error") or result.get("_invalid_payload"):
        return "unknown", "接口令牌状态查询暂时失败，请稍后重试。", None
    if result.get("code") == 200 and result.get("valid") is not False:
        detail = result.get("detail") if isinstance(result.get("detail"), dict) else {}
        remaining = detail.get("remaining")
        if remaining is not None:
            try:
                remaining = int(remaining)
            except (TypeError, ValueError):
                remaining = None
            if remaining == 0:
                return "failed", "接口令牌剩余次数为 0。", remaining
        return "ok", "", remaining
    detail = str(result.get("msg") or "")
    kind, raw = credential_failure(detail, result.get("_code"))
    if kind == "token":
        return "failed", credential_message("token", raw), None
    return "unknown", detail or "接口令牌状态查询失败。", None


async def validate_pool_ticket(jx3api, value: str, probe_token: str = "") -> tuple[bool, str, bool]:
    """Validate one ticket. The third value marks a retryable failure."""
    last_reason = ""
    retryable = False
    for _ in range(3):
        ok, reason, retryable = await jx3api.validate_ticket_ex(value, probe_token)
        if ok:
            return True, "", retryable
        last_reason = reason
        if not retryable:
            return False, reason, False
    return False, last_reason or "推栏标识校验失败。", retryable


async def confirm_ticket_failure(jx3api, value: str, probe_token: str = "") -> tuple[bool, str]:
    """Confirm a runtime ticket failure three times before deleting it."""
    reasons: list[str] = []
    confirmed = 0
    for _ in range(3):
        ok, reason, retryable = await jx3api.validate_ticket_ex(value, probe_token)
        if ok:
            return False, "推栏标识状态正常"
        if retryable:
            reasons.append(reason or "接口请求失败")
            continue
        confirmed += 1
        reasons.append(reason or "推栏标识不可用")
    if confirmed == 3:
        lowered_reasons = [item.lower() for item in reasons]
        if all(
            any(key in item for key in ("invalid", "expire", "expired", "失效"))
            for item in lowered_reasons
        ):
            return True, "推栏标识已失效。"
        return True, credential_message("ticket", " / ".join(reasons))
    return False, "推栏标识状态未能确认失效：" + " / ".join(reasons)


def masked_credential(value: str) -> str:
    return mask_for_user(value)
