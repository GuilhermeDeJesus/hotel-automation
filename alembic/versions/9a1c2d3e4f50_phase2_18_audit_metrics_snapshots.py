"""phase2.18 audit metrics snapshots

Revision ID: 9a1c2d3e4f50
Revises: 4e7b9c1a2f10
Create Date: 2026-03-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9a1c2d3e4f50"
down_revision = "4e7b9c1a2f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saas_audit_metrics_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("total_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rate_limited_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rate_limited_ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("alert_status", sa.String(length=20), nullable=False, server_default="healthy"),
        sa.Column("warning_threshold", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("critical_threshold", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("by_outcome_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("top_ips_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_saas_audit_metrics_snapshots_snapshot_date",
        "saas_audit_metrics_snapshots",
        ["snapshot_date"],
        unique=True,
    )
    op.create_index(
        "ix_saas_audit_metrics_snapshots_created_at",
        "saas_audit_metrics_snapshots",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_saas_audit_metrics_snapshots_created_at", table_name="saas_audit_metrics_snapshots")
    op.drop_index("ix_saas_audit_metrics_snapshots_snapshot_date", table_name="saas_audit_metrics_snapshots")
    op.drop_table("saas_audit_metrics_snapshots")
