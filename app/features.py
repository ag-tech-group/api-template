"""Environment-variable-backed feature flags."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends

from app.auth import current_active_user
from app.models.user import User

router = APIRouter(tags=["features"])

# Prefix used to discover feature flags from the environment.
_ENV_PREFIX = "FEATURE_"


class FeatureFlags:
    """Read ``FEATURE_*`` env vars at startup and expose a simple query API."""

    def __init__(self) -> None:
        self._flags: dict[str, bool] = {}
        for key, value in os.environ.items():
            if key.startswith(_ENV_PREFIX):
                flag_name = key[len(_ENV_PREFIX) :].lower()
                self._flags[flag_name] = value.lower() in {"1", "true", "yes"}

    def is_enabled(self, flag_name: str, *, context: dict[str, Any] | None = None) -> bool:
        """Return whether *flag_name* is enabled.

        An optional *context* dict (e.g. user info) is accepted for future
        targeting support but is currently unused.
        """
        return self._flags.get(flag_name, False)

    def all_flags(self) -> dict[str, bool]:
        """Return a copy of every registered flag and its current state."""
        return dict(self._flags)


# Module-level singleton — initialised once at import time.
feature_flags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """FastAPI dependency returning the feature flags singleton."""
    return feature_flags


@router.get("/flags")
async def list_flags(
    user: User = Depends(current_active_user),
    flags: FeatureFlags = Depends(get_feature_flags),
) -> dict[str, bool]:
    """Return enabled feature flags for the current user."""
    return flags.all_flags()
