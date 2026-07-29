"""add project analysis fields

Revision ID: 494f8a2baf87
Revises: 2d29ffe378be
Create Date: 2026-07-11 16:12:12.893658

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '494f8a2baf87'
down_revision: Union[str, None] = '2d29ffe378be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "analysis_status",
            sa.String(length=50),
            nullable=False,
            server_default="not_started",
        ),
    )

    op.add_column(
        "projects",
        sa.Column(
            "analysis_data",
            sa.JSON(),
            nullable=True,
        ),
    )

    op.add_column(
        "projects",
        sa.Column(
            "analysis_error",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "projects",
        sa.Column(
            "analysis_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "projects",
        sa.Column(
            "analysis_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.alter_column(
        "projects",
        "analysis_status",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("projects", "analysis_completed_at")
    op.drop_column("projects", "analysis_started_at")
    op.drop_column("projects", "analysis_error")
    op.drop_column("projects", "analysis_data")
    op.drop_column("projects", "analysis_status")