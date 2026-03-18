"""payments_unique_per_hotel

Revision ID: b1d3a4c5e6f7
Revises: c9f2c8c3b1d4
Create Date: 2026-03-18

Torna `payments.transaction_id` único por hotel (multi-tenant):
- remove UNIQUE global em `transaction_id`
- adiciona UNIQUE composto em (`hotel_id`, `transaction_id`)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1d3a4c5e6f7"
down_revision = "c9f2c8c3b1d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # O `unique=True` em `transaction_id` cria uma constraint/index global.
    # Como o nome exato pode variar entre bancos/geradores, tentamos remover
    # com segurança (IF EXISTS).
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'payments_transaction_id_key'
            ) THEN
                ALTER TABLE payments DROP CONSTRAINT payments_transaction_id_key;
            END IF;

            -- fallback para possíveis nomes de índices
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'payments' AND indexname = 'uq_payments_transaction_id'
            ) THEN
                DROP INDEX uq_payments_transaction_id;
            END IF;

            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'payments' AND indexname = 'ix_payments_transaction_id'
            ) THEN
                DROP INDEX ix_payments_transaction_id;
            END IF;
        END $$;
        """
    )

    op.create_unique_constraint(
        "uq_payments_hotel_transaction_id",
        "payments",
        ["hotel_id", "transaction_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_payments_hotel_transaction_id",
        "payments",
        type_="unique",
    )

    # Recria UNIQUE global para `transaction_id` (nome pode variar conforme SGBD).
    op.create_unique_constraint(
        "payments_transaction_id_key",
        "payments",
        ["transaction_id"],
    )

