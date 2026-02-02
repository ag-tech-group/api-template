from enum import StrEnum

from fastapi import Depends, HTTPException, status

from app.auth.users import current_active_user
from app.models.user import User


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


def require_role(*allowed_roles: str):
    """Dependency factory that checks the user has one of the allowed roles.

    Superusers bypass the role check. Returns the authenticated User so
    routes don't need a separate ``Depends(current_active_user)``.
    """

    async def _check_role(user: User = Depends(current_active_user)) -> User:
        if user.is_superuser:
            return user
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check_role
