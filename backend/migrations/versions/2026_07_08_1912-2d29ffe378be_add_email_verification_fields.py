"""add_email_verification_fields

Revision ID: 2d29ffe378be
Revises: 299d3ba2b20f
Create Date: 2026-07-08 19:12:30.450794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d29ffe378be'
down_revision: Union[str, None] = '299d3ba2b20f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "email_verification_token_hash",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "email_verification_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_users_email_verification_token_hash"),
        "users",
        ["email_verification_token_hash"],
        unique=False,
    )

    # Les anciens comptes déjà créés pendant le développement restent utilisables.
    op.execute("UPDATE users SET is_email_verified = TRUE")


def downgrade() -> None:
    op.drop_index(op.f("ix_users_email_verification_token_hash"), table_name="users")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "is_email_verified")