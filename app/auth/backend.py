from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

from app.config import settings

ACCESS_TOKEN_LIFETIME = 900  # 15 minutes

cookie_transport = CookieTransport(
    cookie_name="app_access",
    cookie_max_age=ACCESS_TOKEN_LIFETIME,
    cookie_path="/",
    cookie_domain=settings.cookie_domain,
    cookie_secure=not settings.is_development,
    cookie_httponly=True,
    cookie_samesite=settings.cookie_samesite,
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.secret_key, lifetime_seconds=ACCESS_TOKEN_LIFETIME)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
