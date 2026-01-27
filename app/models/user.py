from fastapi_users.db import SQLAlchemyBaseUserTableUUID

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

    Add custom fields below if needed, e.g.:
        display_name: Mapped[str | None] = mapped_column(String(100))
    """

    pass
