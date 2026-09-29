"""index on lower(users.email): case-insensitive e-mail lookups stay fast

Revision ID: f4a2b6c8d013
Revises: e3c1a7d5b902
Create Date: 2026-09-28 15:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a2b6c8d013"
down_revision: Union[str, None] = "e3c1a7d5b902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Not unique on purpose: accounts created before the normalisation may
    # differ only by case; new accounts are stored lowercase.
    op.create_index("ix_users_email_lower", "users", [sa.text("lower(email)")])


def downgrade() -> None:
    op.drop_index("ix_users_email_lower", table_name="users")
