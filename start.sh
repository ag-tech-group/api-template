#!/bin/sh
set -e

# Apply any pending database migrations
uv run alembic upgrade head

# Start the application
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
