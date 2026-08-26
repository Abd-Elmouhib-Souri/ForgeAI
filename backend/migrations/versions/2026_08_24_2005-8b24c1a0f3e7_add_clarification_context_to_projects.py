"""add clarification_context to projects

Revision ID: 8b24c1a0f3e7
Revises: c4f8a2d19e7b
Create Date: 2026-08-24 20:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b24c1a0f3e7"

down_revision: Union[
    str,
    None,
] = "c4f8a2d19e7b"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "clarification_context",
            sa.JSON(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "projects",
        "clarification_context",
    )
