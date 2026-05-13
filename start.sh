#!/bin/sh
set -e

# Apply any pending database migrations
uv run alembic upgrade head

# Start the application.
# --proxy-headers --forwarded-allow-ips='*' makes uvicorn trust the
# X-Forwarded-For / X-Forwarded-Proto headers set by the upstream proxy
# (Cloud Run, an ALB, nginx, ...), so request.client.host is the real client IP
# rather than the proxy's internal address. The rate limiter keys on that IP, so
# without this every request collapses into one bucket. '*' trusts any upstream —
# correct when the service is ALWAYS behind a proxy that overwrites these headers;
# if it can also be reached directly, restrict this to the proxy's IP range.
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
    --proxy-headers --forwarded-allow-ips='*'
