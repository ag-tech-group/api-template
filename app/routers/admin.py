from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.roles import UserRole, require_role
from app.database import get_async_session
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/admin", tags=["admin"])


class RoleUpdate(BaseModel):
    role: str


@router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: UUID,
    body: RoleUpdate,
    session: AsyncSession = Depends(get_async_session),
    _admin: User = Depends(require_role("admin")),
):
    """Update a user's role. Requires admin role."""
    # Validate role value against enum
    try:
        UserRole(body.role)
    except ValueError:
        valid = [r.value for r in UserRole]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid role '{body.role}'. Must be one of: {valid}",
        ) from None

    target = await session.get(User, user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    target.role = body.role
    await session.commit()
    await session.refresh(target)
    return target
