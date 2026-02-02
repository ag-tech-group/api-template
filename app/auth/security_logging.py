from enum import StrEnum

import structlog
from fastapi import Request

logger = structlog.get_logger("app.security")


class SecurityEvent(StrEnum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    RATE_LIMIT_HIT = "RATE_LIMIT_HIT"


def log_security_event(
    event: SecurityEvent,
    *,
    request: Request | None = None,
    user_id: str | None = None,
    email: str | None = None,
    detail: str | None = None,
) -> None:
    ip = None
    user_agent = None
    if request is not None:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    request_id = None
    if request is not None:
        request_id = getattr(request.state, "request_id", None)

    logger.info(
        "security_event",
        security_event=event.value,
        ip=ip,
        user_agent=user_agent,
        user_id=user_id,
        email=email,
        detail=detail,
        request_id=request_id,
    )
