"""phase2.12 saas admin audit events

Revision ID: 4e7b9c1a2f10
Revises: 8b3c2e1f9c4a
Create Date: 2026-03-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4e7b9c1a2f10"
down_revision = "8b3c2e1f9c4a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saas_admin_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("client_ip", sa.String(length=80), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("deleted_keys", sa.Integer(), nullable=True),
        sa.Column("retry_after", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_saas_admin_audit_events_event_type",
        "saas_admin_audit_events",
        ["event_type"],
    )
    op.create_index(
        "ix_saas_admin_audit_events_client_ip",
        "saas_admin_audit_events",
        ["client_ip"],
    )
    op.create_index(
        "ix_saas_admin_audit_events_outcome",
        "saas_admin_audit_events",
        ["outcome"],
    )
    op.create_index(
        "ix_saas_admin_audit_events_created_at",
        "saas_admin_audit_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_saas_admin_audit_events_created_at", table_name="saas_admin_audit_events")
    op.drop_index("ix_saas_admin_audit_events_outcome", table_name="saas_admin_audit_events")
    op.drop_index("ix_saas_admin_audit_events_client_ip", table_name="saas_admin_audit_events")
    op.drop_index("ix_saas_admin_audit_events_event_type", table_name="saas_admin_audit_events")
    op.drop_table("saas_admin_audit_events")
