from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import auth_backend, fastapi_users
from app.config import settings
from app.routers import racers_router
from app.schemas.user import UserCreate, UserRead

app = FastAPI(
    title="API Template",
    description="FastAPI template with async PostgreSQL and JWT auth",
    version="0.1.0",
)

# CORS configuration - adjust origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth routes (remove this section if you don't need authentication) ---
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

# API routes
app.include_router(racers_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "API Template"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {"status": "healthy"}
