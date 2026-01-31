import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Response
from fastapi_users.jwt import decode_jwt, generate_jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.refresh_token import RefreshToken

REFRESH_TOKEN_LIFETIME = timedelta(days=7)
REFRESH_COOKIE_NAME = "app_refresh"
REFRESH_AUDIENCE = ["app:refresh"]


async def create_refresh_token(
    user_id: str,
    session: AsyncSession,
    family: str | None = None,
) -> str:
    token_id = uuid.uuid4()
    token_family = family or uuid.uuid4().hex
    expires_at = datetime.now(UTC) + REFRESH_TOKEN_LIFETIME

    db_token = RefreshToken(
        id=token_id,
        user_id=uuid.UUID(user_id),
        token_family=token_family,
        is_revoked=False,
        expires_at=expires_at,
    )
    session.add(db_token)
    await session.commit()

    jwt_data = {
        "sub": user_id,
        "jti": str(token_id),
        "family": token_family,
        "aud": REFRESH_AUDIENCE,
    }
    return generate_jwt(
        jwt_data,
        secret=settings.secret_key,
        lifetime_seconds=int(REFRESH_TOKEN_LIFETIME.total_seconds()),
    )


async def validate_and_rotate_refresh_token(
    token_jwt: str,
    session: AsyncSession,
) -> tuple[str, str] | None:
    try:
        payload = decode_jwt(
            token_jwt,
            secret=settings.secret_key,
            audience=REFRESH_AUDIENCE,
        )
    except Exception:
        return None

    jti = payload.get("jti")
    user_id = payload.get("sub")
    family = payload.get("family")

    if not jti or not user_id or not family:
        return None

    # Look up the token in DB
    result = await session.execute(select(RefreshToken).where(RefreshToken.id == uuid.UUID(jti)))
    db_token = result.scalar_one_or_none()

    if db_token is None:
        return None

    # If revoked, this is a reuse — revoke the entire family (theft detection)
    if db_token.is_revoked:
        await session.execute(
            update(RefreshToken).where(RefreshToken.token_family == family).values(is_revoked=True)
        )
        await session.commit()
        return None

    # Check expiration
    if db_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        return None

    # Revoke the current token
    db_token.is_revoked = True
    await session.flush()

    # Issue a new token in the same family
    new_jwt = await create_refresh_token(user_id, session, family=family)

    return (user_id, new_jwt)


def set_refresh_cookie(response: Response, jwt: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=jwt,
        max_age=int(REFRESH_TOKEN_LIFETIME.total_seconds()),
        path="/auth/refresh",
        domain=settings.cookie_domain,
        secure=not settings.is_development,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/auth/refresh",
        domain=settings.cookie_domain,
        secure=not settings.is_development,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


async def cleanup_expired_tokens(session: AsyncSession) -> int:
    result = await session.execute(
        select(RefreshToken).where(
            (RefreshToken.expires_at < datetime.now(UTC)) | (RefreshToken.is_revoked == True)  # noqa: E712
        )
    )
    tokens = result.scalars().all()
    count = len(tokens)
    for token in tokens:
        await session.delete(token)
    await session.commit()
    return count
