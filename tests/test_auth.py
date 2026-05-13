import importlib
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi_users.jwt import generate_jwt
from httpx import AsyncClient
from sqlalchemy import select

from app.auth.refresh import REFRESH_AUDIENCE, REFRESH_COOKIE_NAME, REFRESH_TOKEN_LIFETIME
from app.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User


def _make_refresh_jwt(user_id: UUID, jti: UUID, family: str) -> str:
    return generate_jwt(
        {
            "sub": str(user_id),
            "jti": str(jti),
            "family": family,
            "aud": REFRESH_AUDIENCE,
        },
        secret=settings.secret_key,
        lifetime_seconds=int(REFRESH_TOKEN_LIFETIME.total_seconds()),
    )


class TestLogoutRevocation:
    """Reproducer for the silent-failure bug: logout must revoke the token family."""

    async def test_logout_revokes_token_family(self, client: AsyncClient, test_user: User, session):
        session.add(test_user)
        await session.commit()

        family = "family-under-test"
        jti = uuid4()
        db_token = RefreshToken(
            id=jti,
            user_id=test_user.id,
            token_family=family,
            is_revoked=False,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(db_token)
        await session.commit()

        response = await client.post(
            "/v1/auth/jwt/logout",
            cookies={REFRESH_COOKIE_NAME: _make_refresh_jwt(test_user.id, jti, family)},
        )
        assert response.status_code == 204

        await session.refresh(db_token)
        assert db_token.is_revoked is True

    async def test_logout_revokes_all_tokens_in_family(
        self, client: AsyncClient, test_user: User, session
    ):
        """Multiple rotated tokens in one family: logout revokes every row."""
        session.add(test_user)
        await session.commit()

        family = "shared-family"
        tokens = [
            RefreshToken(
                id=uuid4(),
                user_id=test_user.id,
                token_family=family,
                is_revoked=False,
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
            for _ in range(3)
        ]
        for t in tokens:
            session.add(t)
        await session.commit()

        response = await client.post(
            "/v1/auth/jwt/logout",
            cookies={REFRESH_COOKIE_NAME: _make_refresh_jwt(test_user.id, tokens[-1].id, family)},
        )
        assert response.status_code == 204

        # Endpoint ran the UPDATE in its own session; expire this session's
        # identity map so the re-query reflects the committed changes.
        session.expire_all()
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_family == family)
        )
        rows = result.scalars().all()
        assert len(rows) == 3
        assert all(row.is_revoked for row in rows)

    async def test_logout_with_invalid_token_returns_204(self, client: AsyncClient):
        """Malformed cookie: logout still succeeds (user-facing) and does not crash."""
        response = await client.post(
            "/v1/auth/jwt/logout",
            cookies={REFRESH_COOKIE_NAME: "not-a-real-jwt"},
        )
        assert response.status_code == 204

    async def test_logout_without_cookie_returns_204(self, client: AsyncClient):
        response = await client.post("/v1/auth/jwt/logout")
        assert response.status_code == 204


class TestCookiePrefixWiring:
    """COOKIE_PREFIX must flow through to every cookie surface."""

    def test_cookie_names_compose_from_settings_prefix(self):
        from app.auth.backend import cookie_transport
        from app.auth.refresh import REFRESH_COOKIE_NAME as current_refresh_name

        assert cookie_transport.cookie_name == f"{settings.cookie_prefix}_access"
        assert current_refresh_name == f"{settings.cookie_prefix}_refresh"

    def test_cookie_prefix_env_override_wires_through(self):
        """Changing COOKIE_PREFIX changes the computed cookie names end-to-end.

        This is the test that distinguishes "reads from the setting" from
        "happens to produce the right string because the default is 'app'".
        """
        import app.auth.backend as backend_mod
        import app.auth.refresh as refresh_mod
        import app.config as config_mod

        original = os.environ.get("COOKIE_PREFIX")
        os.environ["COOKIE_PREFIX"] = "verify_prefix"
        try:
            importlib.reload(config_mod)
            importlib.reload(backend_mod)
            importlib.reload(refresh_mod)
            assert backend_mod.cookie_transport.cookie_name == "verify_prefix_access"
            assert refresh_mod.REFRESH_COOKIE_NAME == "verify_prefix_refresh"
        finally:
            if original is None:
                os.environ.pop("COOKIE_PREFIX", None)
            else:
                os.environ["COOKIE_PREFIX"] = original
            importlib.reload(config_mod)
            importlib.reload(backend_mod)
            importlib.reload(refresh_mod)
