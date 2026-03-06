"""hotel payment config (10.6)

Revision ID: a1b2c3d4e5f6
Revises: 9a1c2d3e4f50
Create Date: 2026-03-06

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "9a1c2d3e4f50"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hotels",
        sa.Column(
            "requires_payment_for_confirmation",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "hotels",
        sa.Column(
            "allows_reservation_without_payment",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("hotels", "allows_reservation_without_payment")
    op.drop_column("hotels", "requires_payment_for_confirmation")
