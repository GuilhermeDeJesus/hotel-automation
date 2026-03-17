"""multi_tenant_unique_constraints

Revision ID: f854841574ad
Revises: b2c3d4e5f6a1
Create Date: 2026-03-16 23:23:01.267387

Ajusta constraints de unicidade para suportar multi-tenant:
- rooms: número único por hotel (hotel_id, number)
- customers: documento único por hotel (hotel_id, document)
- conversation_cache: phone único por hotel (hotel_id, phone_number)
- saas_leads: phone único por hotel (hotel_id, phone_number)
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f854841574ad'
down_revision = None  # Primeira migration - banco já criado por migration.sql/create_all
branch_labels = None
depends_on = None


def upgrade() -> None:
    # rooms: remover unique antigo em number, adicionar unique (hotel_id, number)
    op.drop_index('ix_rooms_number', table_name='rooms')
    op.create_unique_constraint('uq_rooms_hotel_number', 'rooms', ['hotel_id', 'number'])
    op.create_index('ix_rooms_number', 'rooms', ['number'], unique=False)

    # customers: remover unique em document, adicionar unique (hotel_id, document)
    op.drop_constraint('customers_document_key', 'customers', type_='unique')
    op.create_unique_constraint('uq_customers_hotel_document', 'customers', ['hotel_id', 'document'])

    # conversation_cache: remover unique em phone_number, adicionar unique (hotel_id, phone_number)
    op.drop_index('ix_conversation_cache_phone_number', table_name='conversation_cache')
    op.create_unique_constraint('uq_conversation_cache_hotel_phone', 'conversation_cache', ['hotel_id', 'phone_number'])
    op.create_index('ix_conversation_cache_phone_number', 'conversation_cache', ['phone_number'], unique=False)

    # saas_leads: remover unique em phone_number, adicionar unique (hotel_id, phone_number)
    op.drop_index('ix_saas_leads_phone_number', table_name='saas_leads')
    op.create_unique_constraint('uq_saas_leads_hotel_phone', 'saas_leads', ['hotel_id', 'phone_number'])
    op.create_index('ix_saas_leads_phone_number', 'saas_leads', ['phone_number'], unique=False)


def downgrade() -> None:
    # saas_leads: reverter
    op.drop_constraint('uq_saas_leads_hotel_phone', 'saas_leads', type_='unique')
    op.drop_index('ix_saas_leads_phone_number', table_name='saas_leads')
    op.create_index('ix_saas_leads_phone_number', 'saas_leads', ['phone_number'], unique=True)

    # conversation_cache: reverter
    op.drop_constraint('uq_conversation_cache_hotel_phone', 'conversation_cache', type_='unique')
    op.drop_index('ix_conversation_cache_phone_number', table_name='conversation_cache')
    op.create_index('ix_conversation_cache_phone_number', 'conversation_cache', ['phone_number'], unique=True)

    # customers: reverter
    op.drop_constraint('uq_customers_hotel_document', 'customers', type_='unique')
    op.create_unique_constraint('customers_document_key', 'customers', ['document'])

    # rooms: reverter
    op.drop_constraint('uq_rooms_hotel_number', 'rooms', type_='unique')
    op.drop_index('ix_rooms_number', table_name='rooms')
    op.create_index('ix_rooms_number', 'rooms', ['number'], unique=True)
