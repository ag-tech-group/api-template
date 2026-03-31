"""add user name column

Revision ID: c4e8f2a1b5d7
Revises: b3c7a1d9e2f4
Create Date: 2026-03-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e8f2a1b5d7"
down_revision: str | Sequence[str] | None = "b3c7a1d9e2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add name column to user table."""
    op.add_column("user", sa.Column("name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove name column from user table."""
    op.drop_column("user", "name")
