from contextvars import ContextVar

_request_token: ContextVar[str | None] = ContextVar("jx3_request_token", default=None)
_request_ticket: ContextVar[str | None] = ContextVar("jx3_request_ticket", default=None)


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
