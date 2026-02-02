"""add user role column

Revision ID: b3c7a1d9e2f4
Revises: af85030565fd
Create Date: 2026-02-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c7a1d9e2f4"
down_revision: str | Sequence[str] | None = "af85030565fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add role column to user table."""
    op.add_column(
        "user", sa.Column("role", sa.String(length=50), server_default="user", nullable=False)
    )


def downgrade() -> None:
    """Remove role column from user table."""
    op.drop_column("user", "role")
