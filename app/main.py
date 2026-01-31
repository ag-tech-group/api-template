from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from limits import RateLimitItem, parse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.auth import auth_backend, current_active_user, fastapi_users
from app.auth.security_logging import SecurityEvent, log_security_event
from app.config import settings
from app.models.user import User
from app.routers import notes_router
from app.routers.auth_refresh import router as auth_refresh_router
from app.schemas.user import UserCreate, UserRead

app = FastAPI(
    title="API Template",
    description="FastAPI template with async PostgreSQL and cookie-based JWT auth",
    version="0.2.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Auth routes ---
# Custom refresh/logout routes (included before FastAPI-Users so /auth/jwt/logout is shadowed)
app.include_router(auth_refresh_router)
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
# --- End auth routes ---


@app.get("/auth/me", response_model=UserRead, tags=["auth"])
async def get_current_user(user: User = Depends(current_active_user)):
    return user


# Path-specific rate limits for auth endpoints
_AUTH_RATE_LIMITS: dict[str, RateLimitItem] = {
    "/auth/jwt/login": parse("5/minute"),
    "/auth/register": parse("3/minute"),
    "/auth/refresh": parse("30/minute"),
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


# API routes
app.include_router(notes_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "API Template"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {"status": "healthy"}
