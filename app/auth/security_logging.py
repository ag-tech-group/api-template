import logging
from enum import StrEnum

from fastapi import Request

logger = logging.getLogger("app.security")


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

    extra = {
        "security_event": event.value,
        "ip": ip,
        "user_agent": user_agent,
        "user_id": user_id,
        "email": email,
    }

    message = f"[{event.value}]"
    if email:
        message += f" email={email}"
    if user_id:
        message += f" user_id={user_id}"
    if ip:
        message += f" ip={ip}"
    if detail:
        message += f" {detail}"

    logger.info(message, extra=extra)
