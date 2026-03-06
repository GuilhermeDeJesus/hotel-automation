"""phase2 saas metrics and leads

Revision ID: 8b3c2e1f9c4a
Revises: 5fa085db2e97
Create Date: 2026-03-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8b3c2e1f9c4a"
down_revision = "5fa085db2e97"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saas_leads",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_saas_leads_phone_number", "saas_leads", ["phone_number"], unique=True)
    op.create_index("ix_saas_leads_source", "saas_leads", ["source"])
    op.create_index("ix_saas_leads_stage", "saas_leads", ["stage"])
    op.create_index("ix_saas_leads_first_seen_at", "saas_leads", ["first_seen_at"])
    op.create_index("ix_saas_leads_last_seen_at", "saas_leads", ["last_seen_at"])

    op.create_table(
        "saas_analytics_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_saas_analytics_events_phone_number", "saas_analytics_events", ["phone_number"])
    op.create_index("ix_saas_analytics_events_source", "saas_analytics_events", ["source"])
    op.create_index("ix_saas_analytics_events_event_type", "saas_analytics_events", ["event_type"])
    op.create_index("ix_saas_analytics_events_created_at", "saas_analytics_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_saas_analytics_events_created_at", table_name="saas_analytics_events")
    op.drop_index("ix_saas_analytics_events_event_type", table_name="saas_analytics_events")
    op.drop_index("ix_saas_analytics_events_source", table_name="saas_analytics_events")
    op.drop_index("ix_saas_analytics_events_phone_number", table_name="saas_analytics_events")
    op.drop_table("saas_analytics_events")

    op.drop_index("ix_saas_leads_last_seen_at", table_name="saas_leads")
    op.drop_index("ix_saas_leads_first_seen_at", table_name="saas_leads")
    op.drop_index("ix_saas_leads_stage", table_name="saas_leads")
    op.drop_index("ix_saas_leads_source", table_name="saas_leads")
    op.drop_index("ix_saas_leads_phone_number", table_name="saas_leads")
    op.drop_table("saas_leads")
