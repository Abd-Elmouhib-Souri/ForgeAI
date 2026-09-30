"""add projects.analysis_enqueued_at (Sprint 7.6, analysis relaunch queue)

Revision ID: e3c1a7d5b902
Revises: d7a3c9e1f2b4
Create Date: 2026-09-28 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3c1a7d5b902"
down_revision: Union[str, None] = "d7a3c9e1f2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable: existing projects are simply "not queued".
    op.add_column("projects", sa.Column("analysis_enqueued_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_projects_analysis_enqueued_at", "projects", ["analysis_enqueued_at"])


def downgrade() -> None:
    op.drop_index("ix_projects_analysis_enqueued_at", table_name="projects")
    op.drop_column("projects", "analysis_enqueued_at")
