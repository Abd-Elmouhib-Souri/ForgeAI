"""add analysis run guard fields

Revision ID: a91e6c2b40f1
Revises: 8f1ffc746d6d
Create Date: 2026-07-31 17:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a91e6c2b40f1"
down_revision: Union[str, None] = "8f1ffc746d6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("projects", sa.Column("analysis_run_id", sa.String(length=36), nullable=True))
    op.add_column("projects", sa.Column("analysis_heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("analysis_attempt", sa.Integer(), nullable=False, server_default="0"))
    op.create_index(op.f("ix_projects_analysis_run_id"), "projects", ["analysis_run_id"], unique=False)

def downgrade() -> None:
    op.drop_index(op.f("ix_projects_analysis_run_id"), table_name="projects")
    op.drop_column("projects", "analysis_attempt")
    op.drop_column("projects", "analysis_heartbeat_at")
    op.drop_column("projects", "analysis_run_id")
