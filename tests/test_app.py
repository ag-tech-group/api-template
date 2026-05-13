"""App-level / infrastructure route behaviour: security.txt and global rate limiting."""

from httpx import AsyncClient


class TestSecurityTxt:
    async def test_served_as_plain_text_with_required_fields(self, client: AsyncClient):
        response = await client.get("/.well-known/security.txt")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        body = response.text
        assert "Contact:" in body
        assert "Expires:" in body


class TestGlobalRateLimit:
    """The Limiter's `default_limits` (60/min) applies to every non-exempt route."""

    async def test_default_limit_enforced_on_undecorated_route(self, auth_client: AsyncClient):
        # /v1/notes has no explicit @limiter.limit, so it gets the 60/min default.
        # (Matches `default_limits` in app/main.py — bump both together if changed.)
        for _ in range(60):
            assert (await auth_client.get("/v1/notes")).status_code == 200
        assert (await auth_client.get("/v1/notes")).status_code == 429

    async def test_infrastructure_routes_are_exempt(self, client: AsyncClient):
        # /health, /, /docs, /.well-known/security.txt are @limiter.exempt — many
        # rapid hits (well past the 60/min default) never 429.
        for _ in range(70):
            assert (await client.get("/health")).status_code == 200
        assert (await client.get("/")).status_code == 200
        assert (await client.get("/.well-known/security.txt")).status_code == 200
