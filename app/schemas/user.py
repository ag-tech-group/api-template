from uuid import UUID

from fastapi_users import schemas


class UserRead(schemas.BaseUser[UUID]):
    """Schema for reading user data."""

    pass


class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a new user."""

    pass


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user data."""

    pass
