"""add_hotel_media_table

Revision ID: c9f2c8c3b1d4
Revises: 6c1b8a2c9f4e
Create Date: 2026-03-18

Adiciona tabela para armazenar fotos do hotel e por quarto.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c9f2c8c3b1d4"
down_revision = "6c1b8a2c9f4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hotel_media",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("hotel_id", sa.String(), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("room_number", sa.String(length=10), nullable=True),
        sa.Column("caption", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["hotel_id"], ["hotels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_hotel_media_hotel_scope_room",
        "hotel_media",
        ["hotel_id", "scope", "room_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hotel_media_hotel_scope_room", table_name="hotel_media")
    op.drop_table("hotel_media")

