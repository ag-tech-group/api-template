from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model for authentication.

    Inherits from FastAPI-Users base which provides:
    - id: UUID primary key
    - email: unique email address
    - hashed_password: bcrypt hashed password
    - is_active: whether user can authenticate
    - is_superuser: admin privileges
    - is_verified: email verification status
    """

    role: Mapped[str] = mapped_column(
        String(50), default="user", server_default="user", nullable=False
    )
