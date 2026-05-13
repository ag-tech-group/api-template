<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/logo-dark.png">
  <source media="(prefers-color-scheme: light)" srcset=".github/assets/logo-light.png">
  <img alt="AG Technology Group" src=".github/assets/logo-light.png" width="200">
</picture>

# API Template

[![CI](https://github.com/ag-tech-group/api-template/actions/workflows/ci.yml/badge.svg)](https://github.com/ag-tech-group/api-template/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.12-blue.svg)](https://www.python.org/)

FastAPI template with async PostgreSQL, cookie-based JWT authentication, refresh tokens, and security hardening.

## Table of Contents

- [Tech Stack](#tech-stack)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Running with Docker](#running-with-docker)
- [API Documentation](#api-documentation)
  - [Database Viewer](#database-viewer)
  - [Frontend Integration](#frontend-integration)
- [API Endpoints](#api-endpoints)
  - [Auth](#auth)
  - [Admin](#admin)
  - [Notes (Example CRUD)](#notes-example-crud)
- [Authentication](#authentication)
  - [Role-Based Access Control](#role-based-access-control)
  - [Security Features](#security-features)
- [Logging, Telemetry & Feature Flags](#logging-telemetry--feature-flags)
  - [Structured Logging](#structured-logging)
  - [OpenTelemetry](#opentelemetry)
  - [Analytics](#analytics)
  - [Feature Flags](#feature-flags)
- [Database Migrations](#database-migrations)
  - [Workflow](#workflow)
  - [Common Commands](#common-commands)
- [Testing](#testing)
- [Linting & Formatting](#linting--formatting)
- [Git Setup & Pre-commit Hooks](#git-setup--pre-commit-hooks)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [License](#license)

## Tech Stack

| Component          | Technology                                                                 |
| ------------------ | -------------------------------------------------------------------------- |
| Framework          | [FastAPI](https://fastapi.tiangolo.com/)                                   |
| Database           | [PostgreSQL](https://www.postgresql.org/) (async via [asyncpg](https://magicstack.github.io/asyncpg/)) |
| ORM                | [SQLAlchemy 2.0](https://www.sqlalchemy.org/)                              |
| Migrations         | [Alembic](https://alembic.sqlalchemy.org/)                                 |
| Auth               | [FastAPI-Users](https://fastapi-users.github.io/fastapi-users/) (cookie JWT) |
| Rate Limiting      | [slowapi](https://slowapi.readthedocs.io/)                                 |
| Package Manager    | [uv](https://docs.astral.sh/uv/)                                           |
| Containerization   | [Docker](https://www.docker.com/) / [Docker Compose](https://docs.docker.com/compose/) |
| Testing            | [Pytest](https://docs.pytest.org/) (async via [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)) |
| Linting/Formatting | [Ruff](https://docs.astral.sh/ruff/)                                       |
| Git Hooks          | [pre-commit](https://pre-commit.com/)                                      |

## Requirements

- Python 3.12+
- uv
- Docker & Docker Compose (for local development)

## Quick Start

```bash
# Clone and enter directory
cd api-template

# Copy environment file
cp .env.example .env

# Install dependencies
uv sync

# Start PostgreSQL
docker compose up -d db

# Run migrations
uv run alembic upgrade head

# Start the API
uv run uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## Running with Docker

```bash
# Start everything (API + PostgreSQL + Adminer)
docker compose up

# Or run in background
docker compose up -d
```

## API Documentation

Once running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### Database Viewer

Adminer is available at http://localhost:8080 when running via Docker Compose.

Login: System=PostgreSQL, Server=db, User=postgres, Password=postgres, Database=api_template

### Frontend Integration

This API automatically generates an OpenAPI specification that can be used to generate type-safe clients for frontends. The companion [web-template](https://github.com/ag-tech-group/web-template) uses [orval](https://orval.dev/) to generate React Query hooks and TypeScript types from this spec.

To generate the frontend client:

```bash
# In the frontend project run this or any similar applicable command
pnpm generate-api
```

This requires the API to be running locally (or set `OPENAPI_URL` to point to a deployed instance).

## API Endpoints

All application routes are served under the `/v1` prefix so the API surface can be versioned as a whole — when a breaking change is needed, mount the new routers under `/v2` alongside `/v1`. Infrastructure routes (`/`, `/health`, `/docs`, `/openapi.json`) stay unversioned. Routers are registered in the `ROUTERS` tuple in `app/main.py`, which loop-mounts each one with the `/v1` prefix.

### Auth

| Method | Endpoint               | Description                                |
| ------ | ---------------------- | ------------------------------------------ |
| POST   | `/v1/auth/register`    | Create a new account                       |
| POST   | `/v1/auth/jwt/login`   | Log in (sets access + refresh cookies)     |
| POST   | `/v1/auth/jwt/logout`  | Log out (revokes tokens, clears cookies)   |
| POST   | `/v1/auth/refresh`     | Rotate refresh token, reissue access token |
| GET    | `/v1/auth/me`          | Get current authenticated user             |

### Admin

Admin endpoints require the `admin` role (superusers also have access).

| Method | Endpoint                       | Description          |
| ------ | ------------------------------ | -------------------- |
| PATCH  | `/v1/admin/users/{id}/role`    | Update a user's role |

### Notes (Example CRUD)

All note endpoints require authentication. Users can only access their own notes.

| Method | Endpoint         | Description               |
| ------ | ---------------- | ------------------------- |
| GET    | `/v1/notes`      | List current user's notes |
| GET    | `/v1/notes/{id}` | Get a note by ID          |
| POST   | `/v1/notes`      | Create a note             |
| PATCH  | `/v1/notes/{id}` | Update a note             |
| DELETE | `/v1/notes/{id}` | Delete a note             |

## Authentication

Authentication uses httpOnly cookies with short-lived access tokens and rotating refresh tokens.

- **Access token**: 15-minute JWT stored in a `{COOKIE_PREFIX}_access` httpOnly cookie
- **Refresh token**: 7-day JWT stored in a `{COOKIE_PREFIX}_refresh` httpOnly cookie (scoped to `/v1/auth/refresh` — the cookie's `path` tracks `API_V1_PREFIX` in `app/config.py`)
- **Token rotation**: Each refresh issues a new token in the same family; reuse of an old token revokes the entire family (theft detection)
- **Rate limiting**: 60/min per client IP globally (infrastructure routes exempt), with stricter per-endpoint limits on auth routes — login 5/min, registration 3/min, refresh 30/min. Limits are keyed by client IP, so behind a proxy/load balancer the app must run with uvicorn's `--proxy-headers` (already wired into `start.sh`).

> **Before first deploy**:
>
> - Set `COOKIE_PREFIX` to a service-scoped value (typically your service name, e.g. `myservice`). Browser cookies on the same domain are identified by name, so two services sharing a `.example.com` with the default prefix will overwrite each other's auth cookies. Production startup will refuse to boot with the template defaults `""`, `"app"`, or `"api-template"`.
> - Replace the placeholder `Contact:` in `SECURITY_TXT` (`app/main.py`) with a real security-disclosure address, and bump `Expires:` if it's close.

### Role-Based Access Control

Users have a `role` field (default: `user`). Roles are defined as a `StrEnum` in `app/auth/roles.py`:

- **user** — default role for all registered users
- **admin** — can access admin endpoints (e.g. updating user roles)

Superusers (`is_superuser=True`) bypass all role checks. Roles are read-only via `GET /v1/auth/me` and can only be changed by admins via `PATCH /v1/admin/users/{id}/role`. The `require_role()` dependency factory can be used to gate any route:

```python
from app.auth import require_role

@router.get("/admin-only")
async def admin_only(user: User = Depends(require_role("admin"))):
    ...
```

### Security Features

- **Cookie auth**: httpOnly, Secure (in production), SameSite
- **CORS lockdown**: Explicit origins, methods, and headers (no wildcards in production)
- **Security headers**: HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy
- **Rate limiting**: Global 60/min-per-IP default plus stricter per-endpoint limits on auth routes; rate-limit hits logged as security events
- **Security disclosure**: `/.well-known/security.txt` per [securitytxt.org](https://securitytxt.org/) (set your contact before deploying — see the note above)
- **Production config validation**: Rejects weak secrets, default database credentials, unset cookie prefix, and default OTel service name at startup
- **Security event logging**: Structured logs for login, logout, registration, token refresh, and rate limit events

## Logging, Telemetry & Feature Flags

### Structured Logging

Logging uses [structlog](https://www.structlog.org/) for structured output. In development you get colored console logs; in production, JSON.

Every request is assigned a unique `X-Request-ID` header (or reuses one from the incoming request), and it's automatically bound to all log entries for that request.

Configure via `LOG_LEVEL` env var (default: `INFO`).

### OpenTelemetry

OpenTelemetry tracing is included but disabled by default. To enable, set `OTEL_ENABLED=true` and point `OTEL_EXPORTER_ENDPOINT` at your collector (e.g. Jaeger, Grafana Tempo). FastAPI is auto-instrumented — no code changes needed.

### Analytics

`app/analytics.py` provides an `AnalyticsBackend` protocol with `track()` and `identify()` methods. The default `LogAnalyticsBackend` writes events to structlog. Swap it out by replacing the `analytics` module-level instance with your own implementation (e.g. Segment, PostHog).

Use the `get_analytics()` FastAPI dependency to access it in route handlers.

### Feature Flags

Feature flags are read from `FEATURE_*` environment variables at startup (no database required). Set `FEATURE_<NAME>=true` or `false` in your `.env`.

The `GET /v1/flags` endpoint (requires authentication) returns all flags as a JSON object, consumed by the web-template's `FeatureFlagProvider`.

Use the `get_feature_flags()` dependency in route handlers to check flags server-side via `flags.is_enabled("flag_name")`.

## Database Migrations

This project uses Alembic for database migrations.

### Workflow

1. Edit a model in `app/models/`
2. Generate a migration:
   ```bash
   uv run alembic revision --autogenerate -m "description of change"
   ```
3. Review the generated file in `alembic/versions/` (autogenerate can miss some changes)
4. Apply the migration:
   ```bash
   uv run alembic upgrade head
   ```
5. Commit both the model change and migration file

### Common Commands

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# See current migration status
uv run alembic current

# See migration history
uv run alembic history

# Generate migration without applying
uv run alembic revision --autogenerate -m "description"
```

## Testing

Tests use SQLite in-memory for speed and isolation.

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_notes.py

# Run with coverage
uv run pytest --cov=app
```

The test harness provides `test_user` and `other_user` fixtures for testing user isolation, and an `auth_client` fixture that provides an authenticated HTTP client.

## Linting & Formatting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
# Check for linting errors
uv run ruff check .

# Fix auto-fixable errors
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check formatting without changes
uv run ruff format --check .
```

## Git Setup & Pre-commit Hooks

Initialize git and install pre-commit hooks to auto-format on commit:

```bash
# Initialize git repository
git init

# Install pre-commit hooks
uv run pre-commit install

# Run hooks manually on all files
uv run pre-commit run --all-files
```

Once installed, ruff will automatically check and format your code before each commit.

## Project Structure

```
api-template/
├── app/
│   ├── auth/
│   │   ├── backend.py          # Cookie transport + JWT strategy
│   │   ├── refresh.py          # Refresh token create/rotate/revoke
│   │   ├── roles.py            # UserRole enum + require_role() dependency
│   │   ├── security_logging.py # Structured security event logging
│   │   └── users.py            # UserManager with login/failure hooks
│   ├── models/
│   │   ├── note.py             # Note model (example CRUD entity)
│   │   ├── refresh_token.py    # Refresh token model
│   │   └── user.py             # User model (FastAPI-Users)
│   ├── routers/
│   │   ├── admin.py            # Admin endpoints (role management)
│   │   ├── auth_refresh.py     # /v1/auth/refresh and /v1/auth/jwt/logout
│   │   └── notes.py            # Notes CRUD (user-scoped)
│   ├── schemas/
│   │   ├── note.py             # Note request/response schemas
│   │   └── user.py             # User schemas (FastAPI-Users)
│   ├── analytics.py            # Analytics event abstraction
│   ├── config.py               # Settings with production validation
│   ├── database.py             # Async SQLAlchemy setup
│   ├── features.py             # Feature flags (env-var backed)
│   ├── logging.py              # Structlog configuration
│   ├── telemetry.py            # OpenTelemetry setup
│   └── main.py                 # App entry point, middleware, routes
├── alembic/
│   ├── versions/               # Migration files
│   └── env.py                  # Alembic configuration
├── tests/
│   ├── conftest.py             # Fixtures (client, session, users)
│   ├── test_notes.py           # Notes CRUD + isolation tests
│   └── test_roles.py           # Role-based access control tests
├── .env.example                # Environment template
├── .pre-commit-config.yaml
├── .python-version             # pyenv Python version
├── docker-compose.yml          # API + PostgreSQL + Adminer
├── Dockerfile
└── pyproject.toml
```

## Environment Variables

"Required" means the value **must be set when `ENVIRONMENT=production`** — production config validation rejects the defaults for these. Local development runs out of the box with no env vars set.

| Variable                 | Required     | Description                                       | Default                                                              |
| ------------------------ | ------------ | ------------------------------------------------- | -------------------------------------------------------------------- |
| `ENVIRONMENT`            | Optional     | `development` or `production`                     | `development`                                                        |
| `DATABASE_URL`           | Required     | PostgreSQL connection string                      | `postgresql+asyncpg://postgres:postgres@localhost:5432/api_template` |
| `SECRET_KEY`             | Required     | JWT signing key (min 32 chars in production)      | `change-me-in-production`                                            |
| `CORS_ORIGINS`           | Required     | Comma-separated allowed origins                   | (empty — dev uses localhost:5100-5199)                               |
| `FRONTEND_URL`           | Optional     | Frontend URL for redirects                        | `http://localhost:5173`                                              |
| `COOKIE_DOMAIN`          | Optional     | Cookie domain (leave empty for localhost)         | (empty)                                                              |
| `COOKIE_PREFIX`          | Required     | Prefix for auth cookie names (service-scoped)     | `app`                                                                |
| `LOG_LEVEL`              | Optional     | Logging level                                     | `INFO`                                                               |
| `OTEL_ENABLED`           | Optional     | Enable OpenTelemetry tracing                      | `false`                                                              |
| `OTEL_SERVICE_NAME`      | Required     | Service name for traces                           | `api-template`                                                       |
| `OTEL_EXPORTER_ENDPOINT` | Optional     | OTLP gRPC collector endpoint                      | `http://localhost:4317`                                              |
| `FEATURE_*`              | Optional     | Feature flags (e.g. `FEATURE_NEW_DASHBOARD=true`) | (none)                                                               |

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
