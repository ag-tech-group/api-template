# API Template

FastAPI template with async PostgreSQL, JWT authentication, and database migrations.

## Tech Stack

| Component          | Technology                     |
| ------------------ | ------------------------------ |
| Framework          | FastAPI                        |
| Database           | PostgreSQL (async via asyncpg) |
| ORM                | SQLAlchemy 2.0                 |
| Migrations         | Alembic                        |
| Auth               | FastAPI-Users (JWT)            |
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
# Start everything (API + PostgreSQL)
docker compose up

# Or run in background
docker compose up -d
```

## API Documentation

Once running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

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

| Method | Endpoint          | Description          |
| ------ | ----------------- | -------------------- |
| POST   | `/auth/register`  | Create a new account |
| POST   | `/auth/jwt/login` | Get JWT access token |

### Racers (Example CRUD)

| Method | Endpoint       | Auth | Description       |
| ------ | -------------- | ---- | ----------------- |
| GET    | `/racers`      | No   | List all racers   |
| GET    | `/racers/{id}` | No   | Get a racer by ID |
| POST   | `/racers`      | Yes  | Create a racer    |
| PATCH  | `/racers/{id}` | Yes  | Update a racer    |
| DELETE | `/racers/{id}` | Yes  | Delete a racer    |

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
uv run pytest tests/test_racers.py

# Run with coverage
uv run pytest --cov=app
```

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
│   ├── auth/           # FastAPI-Users JWT setup (removable)
│   ├── models/         # SQLAlchemy models
│   ├── routers/        # API route handlers
│   ├── schemas/        # Pydantic request/response schemas
│   ├── config.py       # Settings from environment
│   ├── database.py     # Async SQLAlchemy setup
│   └── main.py         # FastAPI app entry point
├── alembic/
│   ├── versions/       # Migration files
│   └── env.py          # Alembic configuration
├── tests/
│   ├── conftest.py     # Pytest fixtures
│   └── test_racers.py  # Example tests
├── .env.example        # Environment template
├── .pre-commit-config.yaml
├── .python-version     # pyenv Python version
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Removing Authentication

If your project doesn't need auth, you can remove it:

1. Delete `app/auth/` directory
2. Delete `app/models/user.py` and `app/schemas/user.py`
3. Remove auth imports and routes from `app/main.py`
4. Remove `Depends(current_active_user)` from route handlers
5. Remove `fastapi-users` from `pyproject.toml`
6. Run `uv sync` to update dependencies

## Environment Variables

| Variable       | Description                   | Default                                                              |
| -------------- | ----------------------------- | -------------------------------------------------------------------- |
| `DATABASE_URL` | PostgreSQL connection string  | `postgresql+asyncpg://postgres:postgres@localhost:5432/api_template` |
| `SECRET_KEY`   | JWT signing key               | `change-me-in-production`                                            |
| `ENVIRONMENT`  | `development` or `production` | `development`                                                        |

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
