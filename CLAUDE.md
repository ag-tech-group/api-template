# api-template

FastAPI + async PostgreSQL starter: cookie-based JWT auth (FastAPI-Users) with
refresh-token rotation, SQLAlchemy 2.0 + Alembic, slowapi rate limiting,
structlog, OpenTelemetry, and security headers. The `notes` router is the example
CRUD resource — copy it as the pattern for new resources. See `README.md` for the
full tour.

## How to run things

```bash
uv sync                          # install deps
docker compose up -d db          # local Postgres
uv run alembic upgrade head      # apply migrations
uv run uvicorn app.main:app --reload

# Checks (exactly what CI runs)
uv run pytest                    # test suite (async; in-memory SQLite)
uv run ruff check .              # lint
uv run ruff format --check .     # format (drop --check to apply)

# Migrations
uv run alembic revision -m "describe change"   # stub (autogenerate can miss changes — review it)
uv run alembic upgrade head
```

CI (`.github/workflows/ci.yml`) runs ruff + pytest on every PR to `main`. It does
**not** deploy — see the hardening checklist.

## Conventions

- **Caching is opt-in (default `no-store`).** `cache_control_middleware` in
  `app/main.py` defaults every response to `no-store`; an endpoint that serves
  genuinely public, cacheable data opts in by setting its own `Cache-Control`.
  Never blanket-cache authenticated or mutable responses.
- **Rate limiting keys on the client IP via forwarded headers.**
  `get_remote_address` reads `request.client.host`, which is the real client IP
  only because `start.sh` runs uvicorn with `--proxy-headers`. Behind a proxy/CDN
  that doesn't overwrite `X-Forwarded-For`, key on the CDN's real-client header
  (e.g. `CF-Connecting-IP`) instead, or the whole audience shares one bucket.
- **Tests build the schema with `Base.metadata.create_all` on SQLite — they never
  run Alembic** (`tests/conftest.py`). A migration is only ever exercised against
  real Postgres at deploy time. See hardening.
- **Structured logging via structlog** (`app/logging.py`); JSON in prod. Log
  exception *types*, not just messages (see hardening).

## Production hardening — gotchas learned under real live-event load

> Distilled from running a sibling service through a high-traffic live event.
> These are the general, provider-agnostic ones — worth a read before shipping
> anything derived from this template to production.

- [ ] **Validate migrations against real Postgres before deploy.** The suite uses
  in-memory SQLite via `metadata.create_all` and never runs Alembic, so a bad
  DDL/backfill (a Postgres-only type, constraint timing, a wrong `down_revision`)
  passes CI green and first fails at the deploy's `alembic upgrade head`. Spin up
  a throwaway `postgres:16`, seed realistic pre-migration rows incl. edge cases,
  `upgrade head`, assert data + constraints, and test the `downgrade`.
- [ ] **Schema changes under a rolling deploy: expand → transition → contract,
  never one destructive step.** A rolling deploy serves the old and new revision
  simultaneously during the rollover, so never drop or rename a column the
  still-running revision reads. Three phases: *expand* (add the column,
  dual-write) → *transition* (move reads to it, keep the old column) → *contract*
  (drop the old column once nothing reads it). Aim for zero 5xx per rollover.
- [ ] **Startup readiness must not block on a remote dependency you might need to
  redeploy *through*.** If a process `await`s a DB/upstream call before it binds
  its port and reports healthy, a degraded dependency means the container never
  goes ready — and the deploy that *fixes* that dependency can't roll out. Bind
  the port first; do dependency loading in the background with retry.
- [ ] **Log `type(e).__name__`, not just `str(e)`.** Many transport errors (httpx
  timeouts/connect errors) stringify to `""`, producing un-triageable,
  un-groupable log lines. Always capture the exception type.
- [ ] **Keep full-table reads of static reference data off hot paths.** Reading a
  rarely-changing reference table on every request puts a DB connection
  *checkout* on the hot path — and under a small pool the checkout, not the
  query, is what saturates you under load. Cache it in-process (TTL or
  refresh-on-write).
- [ ] **Don't let a graceful low-level fallback swallow the signal the caller
  needs.** If a helper returns a "usable default" on both a transient failure and
  a permanent one, a retry/backoff loop above it can't tell "retry soon" from
  "this won't get better" and will churn. Surface the failure (raise, or return a
  status); let the caller own the fallback *and* the cadence.
- [ ] **Don't let a correctness-critical value depend on a single soft-failing
  upstream with no floor.** If a denormalized/derived column is computed from one
  upstream field that can come back empty, treat "empty" as a failure mode: encode
  a static floor for the stable mappings, merge upstream over it, and emit a loud
  signal when upstream returns nothing.
- [ ] **Aggregate fan-out failures.** A loop over N entities that logs once per
  failed item turns one upstream blip into an N-line log/alert storm. Aggregate
  per cycle into a single summary (counts by status/type).
- [ ] **Don't double-instrument one call path.** Enabling both ORM and driver
  tracing (e.g. SQLAlchemy *and* asyncpg instrumentation) emits two spans per
  query and multiplies trace volume against your backend's quota for no extra
  signal. Pick one layer.
- [ ] **`merge ≠ deploy` unless CI deploys.** This template's CI lints and tests
  but does not ship — wire your own deploy step and confirm a merge actually
  reaches production, or a merged "fix" can sit undeployed mid-incident.
- [ ] **Don't gate a recovery step behind the step it recovers.** If a
  cleanup/relief step (pruning, scaling, cache-clear) is chained after a step that
  can fail under the very pressure the relief would ease, the failure disables its
  own mitigation. Make recovery steps independent.
- [ ] **Stacked migration PRs: don't rebase a code-only phase onto `main` if a
  *later* stacked phase adds a migration.** Rebasing for a clean diff drops the
  earlier phase's migration from the later branch's history, so its
  `down_revision` resolves to the wrong head. Base the migration-bearing phase on
  the earlier migration branch and cherry-pick the code-only phase onto it.
