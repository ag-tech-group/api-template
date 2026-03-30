FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code and migrations
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini start.sh ./

# Expose port
EXPOSE 8000

# Run migrations then start the application
CMD ["./start.sh"]
