"""add_pix_key_to_hotel_configs

Revision ID: 6c1b8a2c9f4e
Revises: 78fcfc13e18f
Create Date: 2026-03-18

Adiciona coluna pix_key para suportar instruções/chave PIX por hotel.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "6c1b8a2c9f4e"
down_revision = "78fcfc13e18f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hotel_configs",
        sa.Column("pix_key", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hotel_configs", "pix_key")

