"""add output_language to projects

Revision ID: c4f8a2d19e7b
Revises: a91e6c2b40f1
Create Date: 2026-08-17 14:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f8a2d19e7b"
down_revision: Union[str, None] = "a91e6c2b40f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "output_language",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'fr'"),
        ),
    )

    # The server default is used only to backfill existing rows safely.
    # Runtime defaults remain owned by the application model/schema.
    op.alter_column(
        "projects",
        "output_language",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column(
        "projects",
        "output_language",
    )
