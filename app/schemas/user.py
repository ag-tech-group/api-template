from uuid import UUID

from fastapi_users import schemas
from pydantic import Field


class UserRead(schemas.BaseUser[UUID]):
    """Schema for reading user data."""

    name: str | None = None
    role: str = "user"


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user."""

    name: str | None = Field(None, max_length=100)


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user data."""

    name: str | None = Field(None, max_length=100)
