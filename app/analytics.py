"""Analytics event abstraction with a pluggable backend."""

from __future__ import annotations

from typing import Any, Protocol

from app.logging import get_logger

logger = get_logger("app.analytics")


class AnalyticsBackend(Protocol):
    """Protocol that any analytics backend must satisfy."""

    def track(
        self,
        event: str,
        *,
        properties: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> None: ...

    def identify(self, user_id: str, *, traits: dict[str, Any] | None = None) -> None: ...


class LogAnalyticsBackend:
    """Default backend that writes analytics events via structlog."""

    def track(
        self,
        event: str,
        *,
        properties: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> None:
        logger.info(
            "analytics.track",
            analytics_event=event,
            properties=properties or {},
            user_id=user_id,
        )

    def identify(self, user_id: str, *, traits: dict[str, Any] | None = None) -> None:
        logger.info("analytics.identify", user_id=user_id, traits=traits or {})


# Module-level instance — swap with any AnalyticsBackend-compatible object.
analytics: AnalyticsBackend = LogAnalyticsBackend()


def get_analytics() -> AnalyticsBackend:
    """FastAPI dependency returning the current analytics backend."""
    return analytics
