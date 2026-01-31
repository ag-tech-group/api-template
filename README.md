# API Template

FastAPI template with async PostgreSQL, cookie-based JWT authentication, refresh tokens, and security hardening.

## Tech Stack

| Component          | Technology                     |
| ------------------ | ------------------------------ |
| Framework          | FastAPI                        |
| Database           | PostgreSQL (async via asyncpg) |
| ORM                | SQLAlchemy 2.0                 |
| Migrations         | Alembic                        |
| Auth               | FastAPI-Users (cookie JWT)     |
| Rate Limiting      | slowapi                        |
| Package Manager    | uv                             |
| Containerization   | Docker / Docker Compose        |
| Testing            | Pytest (async)                 |
| Linting/Formatting | Ruff                           |
| Git Hooks          | pre-commit                     |

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

This API automatically generates an OpenAPI specification that can be used to generate type-safe clients for frontends. The companion [frontend template](https://github.com/yourusername/web-template) uses [orval](https://orval.dev/) to generate React Query hooks and TypeScript types from this spec.

To generate the frontend client:

```bash
# In the frontend project run this or any similar applicable command
pnpm generate-api
```

This requires the API to be running locally (or set `OPENAPI_URL` to point to a deployed instance).

## API Endpoints

### Auth

| Method | Endpoint            | Description                         |
| ------ | ------------------- | ----------------------------------- |
| POST   | `/auth/register`    | Create a new account                |
| POST   | `/auth/jwt/login`   | Log in (sets access + refresh cookies) |
| POST   | `/auth/jwt/logout`  | Log out (revokes tokens, clears cookies) |
| POST   | `/auth/refresh`     | Rotate refresh token, reissue access token |
| GET    | `/auth/me`          | Get current authenticated user      |

### Notes (Example CRUD)

All note endpoints require authentication. Users can only access their own notes.

| Method | Endpoint      | Description              |
| ------ | ------------- | ------------------------ |
| GET    | `/notes`      | List current user's notes |
| GET    | `/notes/{id}` | Get a note by ID         |
| POST   | `/notes`      | Create a note            |
| PATCH  | `/notes/{id}` | Update a note            |
| DELETE | `/notes/{id}` | Delete a note            |

## Authentication

Authentication uses httpOnly cookies with short-lived access tokens and rotating refresh tokens.

- **Access token**: 15-minute JWT stored in an `app_access` httpOnly cookie
- **Refresh token**: 7-day JWT stored in an `app_refresh` httpOnly cookie (scoped to `/auth/refresh`)
- **Token rotation**: Each refresh issues a new token in the same family; reuse of an old token revokes the entire family (theft detection)
- **Rate limiting**: Login (5/min), registration (3/min), refresh (30/min)

### Security Features

- **Cookie auth**: httpOnly, Secure (in production), SameSite
- **CORS lockdown**: Explicit origins, methods, and headers (no wildcards in production)
- **Security headers**: HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy
- **Rate limiting**: Per-endpoint limits on auth routes with security event logging
- **Production config validation**: Rejects weak secrets and default database credentials at startup
- **Security event logging**: Structured logs for login, logout, registration, token refresh, and rate limit events

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
│   │   ├── security_logging.py # Structured security event logging
│   │   └── users.py            # UserManager with login/failure hooks
│   ├── models/
│   │   ├── note.py             # Note model (example CRUD entity)
│   │   ├── refresh_token.py    # Refresh token model
│   │   └── user.py             # User model (FastAPI-Users)
│   ├── routers/
│   │   ├── auth_refresh.py     # /auth/refresh and /auth/jwt/logout
│   │   └── notes.py            # Notes CRUD (user-scoped)
│   ├── schemas/
│   │   ├── note.py             # Note request/response schemas
│   │   └── user.py             # User schemas (FastAPI-Users)
│   ├── config.py               # Settings with production validation
│   ├── database.py             # Async SQLAlchemy setup
│   └── main.py                 # App entry point, middleware, routes
├── alembic/
│   ├── versions/               # Migration files
│   └── env.py                  # Alembic configuration
├── tests/
│   ├── conftest.py             # Fixtures (client, session, users)
│   └── test_notes.py           # Notes CRUD + isolation tests
├── .env.example                # Environment template
├── .pre-commit-config.yaml
├── .python-version             # pyenv Python version
├── docker-compose.yml          # API + PostgreSQL + Adminer
├── Dockerfile
└── pyproject.toml
```

## Environment Variables

| Variable       | Description                                     | Default                                                              |
| -------------- | ----------------------------------------------- | -------------------------------------------------------------------- |
| `DATABASE_URL` | PostgreSQL connection string                    | `postgresql+asyncpg://postgres:postgres@localhost:5432/api_template` |
| `SECRET_KEY`   | JWT signing key (min 32 chars in production)    | `change-me-in-production`                                            |
| `ENVIRONMENT`  | `development` or `production`                   | `development`                                                        |
| `CORS_ORIGINS` | Comma-separated allowed origins (production)    | (empty — dev uses localhost:5100-5199)                               |
| `FRONTEND_URL` | Frontend URL for redirects                      | `http://localhost:5173`                                              |
| `COOKIE_DOMAIN`| Cookie domain (leave empty for localhost)       | (empty)                                                              |

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
