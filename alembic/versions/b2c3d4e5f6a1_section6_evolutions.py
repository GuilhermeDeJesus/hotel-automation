"""Section 6 - Evoluções (check-in antecipado, compliance, tickets, etc)

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-03-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "b2c3d4e5f6a1"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    return column_name in [c["name"] for c in inspect(conn).get_columns(table_name)]


def _add_column_if_not_exists(table: str, column: sa.Column) -> None:
    conn = op.get_bind()
    if not _column_exists(conn, table, column.name):
        op.add_column(table, column)


def upgrade() -> None:
    conn = op.get_bind()

    # 6.1 Check-in antecipado (idempotente)
    _add_column_if_not_exists("reservations", sa.Column("guest_document", sa.String(20), nullable=True))
    _add_column_if_not_exists("reservations", sa.Column("estimated_arrival_time", sa.String(10), nullable=True))
    _add_column_if_not_exists("reservations", sa.Column("pre_checkin_completed_at", sa.DateTime(), nullable=True))

    # 6.4 Self-check-in e chave digital
    _add_column_if_not_exists("reservations", sa.Column("digital_key_code", sa.String(20), nullable=True))

    # 6.8 Segurança e compliance (LGPD)
    _add_column_if_not_exists(
        "reservations",
        sa.Column("consent_terms_accepted_at", sa.DateTime(), nullable=True),
    )
    _add_column_if_not_exists(
        "reservations",
        sa.Column("consent_marketing", sa.Boolean(), nullable=True, server_default=sa.false()),
    )

    # 6.6 Resolução de problemas (idempotente: tabela pode já existir)
    if not _table_exists(conn, "support_tickets"):
        op.create_table(
            "support_tickets",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("reservation_id", sa.String(), sa.ForeignKey("reservations.id"), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_support_tickets_reservation_id", "support_tickets", ["reservation_id"])
        op.create_index("ix_support_tickets_status", "support_tickets", ["status"])

    # 6.5 Pedidos durante estadia (idempotente)
    if not _table_exists(conn, "room_orders"):
        op.create_table(
            "room_orders",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("reservation_id", sa.String(), sa.ForeignKey("reservations.id"), nullable=False),
            sa.Column("items_json", sa.Text(), nullable=False),
            sa.Column("total_amount", sa.Float(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_room_orders_reservation_id", "room_orders", ["reservation_id"])

    # 6.2 Comunicação proativa - log de mensagens enviadas (idempotente)
    if not _table_exists(conn, "proactive_message_log"):
        op.create_table(
            "proactive_message_log",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("reservation_id", sa.String(), nullable=False),
            sa.Column("message_type", sa.String(50), nullable=False),
            sa.Column("sent_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_proactive_message_log_reservation_id", "proactive_message_log", ["reservation_id"])


def downgrade() -> None:
    op.drop_index("ix_proactive_message_log_reservation_id", table_name="proactive_message_log")
    op.drop_table("proactive_message_log")
    op.drop_index("ix_room_orders_reservation_id", table_name="room_orders")
    op.drop_table("room_orders")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_reservation_id", table_name="support_tickets")
    op.drop_table("support_tickets")
    op.drop_column("reservations", "consent_marketing")
    op.drop_column("reservations", "consent_terms_accepted_at")
    op.drop_column("reservations", "digital_key_code")
    op.drop_column("reservations", "pre_checkin_completed_at")
    op.drop_column("reservations", "estimated_arrival_time")
    op.drop_column("reservations", "guest_document")
