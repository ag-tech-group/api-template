from collections.abc import AsyncGenerator
from uuid import UUID

import structlog
from fastapi import Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import auth_backend
from app.auth.refresh import create_refresh_token, set_refresh_cookie
from app.auth.security_logging import SecurityEvent, log_security_event
from app.config import settings
from app.database import async_session_maker, get_async_session
from app.models.user import User

logger = structlog.get_logger(__name__)


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def on_after_register(self, user: User, request: Request | None = None):
        log_security_event(
            SecurityEvent.REGISTER,
            request=request,
            user_id=str(user.id),
            email=user.email,
        )

    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response: Response | None = None,
    ):
        log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            request=request,
            user_id=str(user.id),
            email=user.email,
        )
        if response is not None:
            async with async_session_maker() as session:
                refresh_jwt = await create_refresh_token(str(user.id), session)
                set_refresh_cookie(response, refresh_jwt)

    async def authenticate(
        self,
        credentials: OAuth2PasswordRequestForm,
    ) -> models.UP | None:
        user = await super().authenticate(credentials)
        if user is None:
            log_security_event(
                SecurityEvent.LOGIN_FAILURE,
                email=credentials.username,
                detail="invalid credentials",
            )
        return user

    async def on_after_forgot_password(self, user: User, token: str, request=None):
        logger.info("Password reset requested for user %s.", user.id)

    async def on_after_request_verify(self, user: User, token: str, request=None):
        logger.info("Email verification requested for user %s.", user.id)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
