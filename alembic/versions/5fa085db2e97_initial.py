"""initial

Revision ID: 5fa085db2e97
Revises: 
Create Date: 2026-02-25 19:02:08.410134

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5fa085db2e97'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("document", sa.String(20), unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_customers_name", "customers", ["name"])
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.create_index("ix_customers_email", "customers", ["email"])

    op.create_table(
        "reservations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("guest_name", sa.String(255), nullable=False),
        sa.Column("guest_phone", sa.String(20), nullable=False),
        sa.Column("customer_id", sa.String(), sa.ForeignKey("customers.id")),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("check_in_date", sa.Date()),
        sa.Column("check_out_date", sa.Date()),
        sa.Column("room_number", sa.String(10)),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("checked_in_at", sa.DateTime()),
        sa.Column("checked_out_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
    )
    op.create_index("ix_reservations_guest_phone", "reservations", ["guest_phone"])
    op.create_index("ix_reservations_status", "reservations", ["status"])

    op.create_table(
        "payments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("reservation_id", sa.String(), sa.ForeignKey("reservations.id"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("payment_method", sa.String(50)),
        sa.Column("transaction_id", sa.String(255), unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("ix_payments_reservation_id", "payments", ["reservation_id"])
    op.create_index("ix_payments_status", "payments", ["status"])

    op.create_table(
        "hotels",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("contact_phone", sa.String(30), nullable=False),
        sa.Column("checkin_time", sa.String(10), nullable=False),
        sa.Column("checkout_time", sa.String(10), nullable=False),
        sa.Column("cancellation_policy", sa.Text(), nullable=False),
        sa.Column("pet_policy", sa.Text(), nullable=False),
        sa.Column("child_policy", sa.Text(), nullable=False),
        sa.Column("amenities", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
    )

    op.create_table(
        "conversation_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("context_data", sa.Text()),
        sa.Column("last_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index(
        "ix_conversation_cache_phone_number",
        "conversation_cache",
        ["phone_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_cache_phone_number", table_name="conversation_cache")
    op.drop_table("conversation_cache")
    op.drop_table("hotels")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_reservation_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_reservations_status", table_name="reservations")
    op.drop_index("ix_reservations_guest_phone", table_name="reservations")
    op.drop_table("reservations")
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_index("ix_customers_name", table_name="customers")
    op.drop_table("customers")
