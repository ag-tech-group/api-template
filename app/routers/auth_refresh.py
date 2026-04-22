from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import cookie_transport, get_jwt_strategy
from app.auth.refresh import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    decode_refresh_token,
    set_refresh_cookie,
    validate_and_rotate_refresh_token,
)
from app.auth.security_logging import SecurityEvent, log_security_event
from app.auth.users import get_user_db
from app.database import get_async_session
from app.models.refresh_token import RefreshToken

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh", status_code=204)
async def refresh_access_token(
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE_NAME),
    session: AsyncSession = Depends(get_async_session),
):
    if not refresh_token:
        return JSONResponse(status_code=401, content={"detail": "Missing refresh token"})

    result = await validate_and_rotate_refresh_token(refresh_token, session)

    if result is None:
        log_security_event(
            SecurityEvent.TOKEN_REFRESH,
            detail="refresh failed — invalid or revoked token",
        )
        response = JSONResponse(status_code=401, content={"detail": "Invalid refresh token"})
        clear_refresh_cookie(response)
        return response

    user_id, new_refresh_jwt = result

    # Load user to generate access token
    async for user_db in get_user_db(session):
        user = await user_db.get(UUID(user_id))
        break

    if user is None or not user.is_active:
        return JSONResponse(status_code=401, content={"detail": "User not found"})

    # Generate new access token
    strategy = get_jwt_strategy()
    access_token = await strategy.write_token(user)

    response = Response(status_code=204)
    # Set access cookie
    response.set_cookie(
        key=cookie_transport.cookie_name,
        value=access_token,
        max_age=cookie_transport.cookie_max_age,
        path=cookie_transport.cookie_path,
        domain=cookie_transport.cookie_domain,
        secure=cookie_transport.cookie_secure,
        httponly=cookie_transport.cookie_httponly,
        samesite=cookie_transport.cookie_samesite,
    )
    # Set new refresh cookie
    set_refresh_cookie(response, new_refresh_jwt)

    log_security_event(
        SecurityEvent.TOKEN_REFRESH,
        user_id=user_id,
        detail="refresh succeeded",
    )

    return response


@router.post("/jwt/logout", status_code=204)
async def logout(
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE_NAME),
    session: AsyncSession = Depends(get_async_session),
):
    # Revoke the refresh-token family if a valid refresh cookie is present.
    # Decode failures → log and proceed (user-facing logout still succeeds).
    # DB errors → propagate as 500, not silently swallowed as "decode failed".
    if refresh_token:
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            log_security_event(SecurityEvent.LOGOUT, detail="refresh token decode failed")
        else:
            family = payload.get("family")
            user_id = payload.get("sub")
            if family:
                await session.execute(
                    update(RefreshToken)
                    .where(RefreshToken.token_family == family)
                    .values(is_revoked=True)
                )
                await session.commit()
                log_security_event(
                    SecurityEvent.LOGOUT,
                    user_id=user_id,
                    detail=f"revoked token family={family}",
                )
    else:
        log_security_event(SecurityEvent.LOGOUT, detail="no refresh token cookie")

    response = Response(status_code=204)
    # Clear access cookie
    cookie_transport._set_logout_cookie(response)
    # Clear refresh cookie
    clear_refresh_cookie(response)

    return response
