import time
import uuid

import structlog
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from limits import RateLimitItem, parse
from scalar_fastapi import get_scalar_api_reference
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.auth import auth_backend, current_active_user, fastapi_users
from app.auth.security_logging import SecurityEvent, log_security_event
from app.config import API_V1_PREFIX, settings
from app.features import router as features_router
from app.logging import setup_logging
from app.models.user import User
from app.routers import admin_router, notes_router
from app.routers.auth_refresh import router as auth_refresh_router
from app.schemas.user import UserCreate, UserRead
from app.telemetry import setup_telemetry

setup_logging()
logger = structlog.get_logger("app.request")

app = FastAPI(
    title="API Template",
    description="FastAPI template with async PostgreSQL and cookie-based JWT auth",
    version="0.2.0",
    docs_url=None,
)

setup_telemetry(app)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rate limiting. `default_limits` applies to every route that isn't decorated
# with its own `@limiter.limit(...)` or marked `@limiter.exempt`; SlowAPIMiddleware
# is what actually enforces it (without the middleware, only explicitly-decorated
# routes are limited). The stricter per-path auth limits in `rate_limit_auth`
# below stack on top of this default — an auth route is subject to both.
# `get_remote_address` reads `request.client.host`, which is the real client IP
# only if uvicorn runs with `--proxy-headers` behind a trusted proxy (see start.sh);
# without that, every request collapses into one bucket and the limit is useless.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

MAX_REQUEST_BODY_SIZE = 1_048_576  # 1 MB


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next) -> Response:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BODY_SIZE:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body too large"},
        )
    return await call_next(request)


# --- Auth routes (mounted under /v1) ---
# Custom refresh/logout routes (included before FastAPI-Users so /v1/auth/jwt/logout is shadowed)
app.include_router(auth_refresh_router, prefix=API_V1_PREFIX)
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix=f"{API_V1_PREFIX}/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix=f"{API_V1_PREFIX}/auth",
    tags=["auth"],
)
# --- End auth routes ---


@app.get(f"{API_V1_PREFIX}/auth/me", response_model=UserRead, tags=["auth"])
async def get_current_user(user: User = Depends(current_active_user)):
    return user


# Path-specific rate limits for auth endpoints
_AUTH_RATE_LIMITS: dict[str, RateLimitItem] = {
    f"{API_V1_PREFIX}/auth/jwt/login": parse("5/minute"),
    f"{API_V1_PREFIX}/auth/register": parse("3/minute"),
    f"{API_V1_PREFIX}/auth/refresh": parse("30/minute"),
}


@app.middleware("http")
async def rate_limit_auth(request: Request, call_next) -> Response:
    """Apply rate limits to auth endpoints."""
    rate_limit = _AUTH_RATE_LIMITS.get(request.url.path)
    if rate_limit and request.method == "POST":
        key = get_remote_address(request)
        if not limiter._limiter.hit(rate_limit, key):
            log_security_event(
                SecurityEvent.RATE_LIMIT_HIT,
                request=request,
                detail=f"path={request.url.path}",
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """Assign a unique request ID to every request."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def cache_control_middleware(request: Request, call_next) -> Response:
    """Set Cache-Control headers: no-store for auth paths, public caching for GETs."""
    response = await call_next(request)
    if request.url.path.startswith(f"{API_V1_PREFIX}/auth/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.method == "GET" and response.status_code == 200:
        response.headers["Cache-Control"] = "public, max-age=3600"
    return response


_HEALTH_PATHS = frozenset(("/", "/health"))


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    """Log method, path, status code, and duration for every request."""
    start = time.perf_counter()
    response = await call_next(request)
    if request.url.path not in _HEALTH_PATHS:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
    return response


# Application routers, all mounted under /v1. Add new resource routers to this
# tuple — they're loop-mounted with the /v1 prefix automatically. (The auth
# routers above are mounted separately because their ordering matters.)
ROUTERS = (
    admin_router,
    notes_router,
    features_router,
)
for router in ROUTERS:
    app.include_router(router, prefix=API_V1_PREFIX)


# Infrastructure routes — not part of the versioned API, and exempt from the
# global rate limit so health-check probes, doc/spec fetches, and automated
# scanners can't burn through the quota.
@app.get("/docs", include_in_schema=False)
@limiter.exempt
async def scalar_docs():
    """Scalar API documentation."""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


@app.get("/")
@limiter.exempt
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "API Template"}


@app.get("/health")
@limiter.exempt
async def health_check():
    """Detailed health check."""
    return {"status": "healthy"}


# Per https://securitytxt.org/ — security researchers and automated scanners look
# for this file to find a disclosure contact. Replace the contact before deploying
# (see the "before first deploy" note in the README) and bump Expires before the
# date below.
SECURITY_TXT = """\
Contact: mailto:security@example.com
Expires: 2027-05-12T00:00:00.000Z
Preferred-Languages: en
"""


@app.get("/.well-known/security.txt", include_in_schema=False)
@limiter.exempt
async def security_txt() -> PlainTextResponse:
    return PlainTextResponse(SECURITY_TXT)
