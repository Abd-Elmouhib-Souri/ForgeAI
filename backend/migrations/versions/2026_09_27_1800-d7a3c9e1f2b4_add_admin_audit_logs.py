"""add admin_audit_logs (Sprint 7.2, append-only)

Revision ID: d7a3c9e1f2b4
Revises: 8b24c1a0f3e7
Create Date: 2026-09-27 18:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7a3c9e1f2b4"
down_revision: Union[str, None] = "8b24c1a0f3e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        # Snapshots, no foreign key: deleting an account keeps its history.
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("target_label", sa.String(length=255), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("detail", sa.String(length=255), nullable=True),
    )
    for column in ("created_at", "actor_id", "actor_email", "action", "result"):
        op.create_index(f"ix_admin_audit_logs_{column}", "admin_audit_logs", [column])

    if op.get_bind().dialect.name == "postgresql":
        # Database-level guard: even a direct SQL session cannot rewrite
        # or erase the trail (the ORM refuses it too, see app.models).
        op.execute(
            """
            CREATE OR REPLACE FUNCTION admin_audit_logs_append_only() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'admin_audit_logs is append-only: % refused', TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER admin_audit_logs_no_rewrite
            BEFORE UPDATE OR DELETE ON admin_audit_logs
            FOR EACH ROW EXECUTE FUNCTION admin_audit_logs_append_only();
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS admin_audit_logs_no_rewrite ON admin_audit_logs;")
        op.execute("DROP FUNCTION IF EXISTS admin_audit_logs_append_only();")
    for column in ("created_at", "actor_id", "actor_email", "action", "result"):
        op.drop_index(f"ix_admin_audit_logs_{column}", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
