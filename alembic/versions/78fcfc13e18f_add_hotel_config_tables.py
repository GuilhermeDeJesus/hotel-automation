"""add_hotel_config_tables

Revision ID: 78fcfc13e18f
Revises: f854841574ad
Create Date: 2026-03-17

Cria tabelas de configuração por hotel: hotel_configs, hotel_themes,
hotel_notifications, hotel_integrations (usadas pela página WhatsApp Config).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '78fcfc13e18f'
down_revision = 'f854841574ad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'hotel_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('hotel_id', sa.String(), nullable=False),
        sa.Column('hotel_name', sa.String(255), nullable=False),
        sa.Column('hotel_description', sa.Text(), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('default_checkin_time', sa.String(10), nullable=False, server_default='14:00'),
        sa.Column('default_checkout_time', sa.String(10), nullable=False, server_default='12:00'),
        sa.Column('early_checkin_fee', sa.Float(), nullable=True, server_default='0'),
        sa.Column('late_checkout_fee', sa.Float(), nullable=True, server_default='0'),
        sa.Column('cancellation_policy_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('cancellation_fee_percentage', sa.Float(), nullable=False, server_default='0'),
        sa.Column('free_cancellation_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('requires_payment_for_confirmation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('payment_methods', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('payment_deadline_hours', sa.Integer(), nullable=True, server_default='24'),
        sa.Column('max_guests_per_room', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('allows_extra_beds', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('extra_bed_fee', sa.Float(), nullable=True, server_default='50'),
        sa.Column('child_policy', sa.Text(), nullable=True),
        sa.Column('pet_policy', sa.Text(), nullable=True),
        sa.Column('smoking_policy', sa.String(20), nullable=False, server_default='NON_SMOKING'),
        sa.Column('breakfast_included', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('breakfast_price', sa.Float(), nullable=True, server_default='0'),
        sa.Column('room_service_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('room_service_hours', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('auto_send_confirmation', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('auto_send_reminder', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('reminder_hours_before', sa.Integer(), nullable=True, server_default='24'),
        sa.Column('whatsapp_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('whatsapp_number', sa.String(50), nullable=True),
        sa.Column('whatsapp_business_hours', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('rate_limit_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('audit_retention_days', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('audit_log_level', sa.String(20), nullable=False, server_default='INFO'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='BRL'),
        sa.Column('language', sa.String(10), nullable=False, server_default='pt-BR'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='America/Sao_Paulo'),
        sa.Column('theme', sa.String(20), nullable=False, server_default='default'),
        sa.Column('primary_color', sa.String(10), nullable=False, server_default='#007bff'),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('active_integrations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('webhook_urls', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('auto_backup_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('backup_frequency_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('backup_retention_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_by', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['hotel_id'], ['hotels.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hotel_id', name='uq_hotel_configs_hotel_id'),
    )
    op.create_index('ix_hotel_configs_hotel_id', 'hotel_configs', ['hotel_id'], unique=True)

    op.create_table(
        'hotel_themes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('hotel_id', sa.String(), nullable=False),
        sa.Column('primary_color', sa.String(10), nullable=False, server_default='#007bff'),
        sa.Column('secondary_color', sa.String(10), nullable=False, server_default='#6c757d'),
        sa.Column('success_color', sa.String(10), nullable=False, server_default='#28a745'),
        sa.Column('warning_color', sa.String(10), nullable=False, server_default='#ffc107'),
        sa.Column('danger_color', sa.String(10), nullable=False, server_default='#dc3545'),
        sa.Column('info_color', sa.String(10), nullable=False, server_default='#17a2b8'),
        sa.Column('body_bg_color', sa.String(10), nullable=False, server_default='#ffffff'),
        sa.Column('header_bg_color', sa.String(10), nullable=False, server_default='#f8f9fa'),
        sa.Column('sidebar_bg_color', sa.String(10), nullable=False, server_default='#343a40'),
        sa.Column('primary_text_color', sa.String(10), nullable=False, server_default='#212529'),
        sa.Column('secondary_text_color', sa.String(10), nullable=False, server_default='#6c757d'),
        sa.Column('muted_text_color', sa.String(10), nullable=False, server_default='#adb5bd'),
        sa.Column('font_family', sa.String(50), nullable=False, server_default='Inter, sans-serif'),
        sa.Column('font_size_base', sa.String(10), nullable=False, server_default='14px'),
        sa.Column('font_weight_normal', sa.String(10), nullable=False, server_default='400'),
        sa.Column('font_weight_bold', sa.String(10), nullable=False, server_default='600'),
        sa.Column('border_radius', sa.String(10), nullable=False, server_default='4px'),
        sa.Column('border_width', sa.String(10), nullable=False, server_default='1px'),
        sa.Column('border_color', sa.String(10), nullable=False, server_default='#dee2e6'),
        sa.Column('shadow_sm', sa.String(50), nullable=False, server_default='0 1px 2px 0 rgba(0, 0, 0, 0.05)'),
        sa.Column('shadow_md', sa.String(50), nullable=False, server_default='0 4px 6px -1px rgba(0, 0, 0, 0.1)'),
        sa.Column('shadow_lg', sa.String(50), nullable=False, server_default='0 10px 15px -3px rgba(0, 0, 0, 0.1)'),
        sa.Column('container_max_width', sa.String(10), nullable=False, server_default='1200px'),
        sa.Column('sidebar_width', sa.String(10), nullable=False, server_default='250px'),
        sa.Column('header_height', sa.String(10), nullable=False, server_default='60px'),
        sa.Column('enable_animations', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('animation_duration', sa.String(10), nullable=False, server_default='0.3s'),
        sa.Column('animation_easing', sa.String(20), nullable=False, server_default='ease-in-out'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_by', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['hotel_id'], ['hotels.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hotel_id', name='uq_hotel_themes_hotel_id'),
    )
    op.create_index('ix_hotel_themes_hotel_id', 'hotel_themes', ['hotel_id'], unique=True)

    op.create_table(
        'hotel_notifications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('hotel_id', sa.String(), nullable=False),
        sa.Column('email_notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_smtp_host', sa.String(255), nullable=True),
        sa.Column('email_smtp_port', sa.Integer(), nullable=True, server_default='587'),
        sa.Column('email_smtp_username', sa.String(255), nullable=True),
        sa.Column('email_smtp_password', sa.String(255), nullable=True),
        sa.Column('email_from_address', sa.String(255), nullable=True),
        sa.Column('email_from_name', sa.String(255), nullable=True),
        sa.Column('email_on_new_reservation', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_on_payment_received', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_on_cancellation', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_on_checkin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('email_on_checkout', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sms_notifications_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sms_provider', sa.String(50), nullable=True),
        sa.Column('sms_api_key', sa.String(255), nullable=True),
        sa.Column('sms_api_secret', sa.String(255), nullable=True),
        sa.Column('sms_from_number', sa.String(50), nullable=True),
        sa.Column('sms_on_new_reservation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sms_on_payment_received', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sms_on_cancellation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sms_on_checkin_reminder', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_vapid_public_key', sa.Text(), nullable=True),
        sa.Column('push_vapid_private_key', sa.Text(), nullable=True),
        sa.Column('push_vapid_email', sa.String(255), nullable=True),
        sa.Column('push_on_new_message', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_on_reservation_update', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_on_payment_status', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('whatsapp_notifications_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('whatsapp_business_api_token', sa.String(255), nullable=True),
        sa.Column('whatsapp_phone_number_id', sa.String(100), nullable=True),
        sa.Column('whatsapp_on_new_reservation', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('whatsapp_on_payment_received', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('whatsapp_on_checkin_reminder', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('whatsapp_on_checkout_reminder', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notification_timezone', sa.String(50), nullable=False, server_default='America/Sao_Paulo'),
        sa.Column('quiet_hours_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quiet_hours_start', sa.String(10), nullable=False, server_default='22:00'),
        sa.Column('quiet_hours_end', sa.String(10), nullable=False, server_default='08:00'),
        sa.Column('max_notifications_per_hour', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_notifications_per_day', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_by', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['hotel_id'], ['hotels.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hotel_id', name='uq_hotel_notifications_hotel_id'),
    )
    op.create_index('ix_hotel_notifications_hotel_id', 'hotel_notifications', ['hotel_id'], unique=True)

    op.create_table(
        'hotel_integrations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('hotel_id', sa.String(), nullable=False),
        sa.Column('integration_type', sa.String(50), nullable=False),
        sa.Column('integration_name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('api_credentials', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sync_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sync_frequency_minutes', sa.Integer(), nullable=True, server_default='60'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('sync_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('webhook_secret', sa.String(255), nullable=True),
        sa.Column('webhook_events', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('field_mapping', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('data_transformation_rules', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('total_syncs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_syncs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_syncs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_by', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['hotel_id'], ['hotels.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_hotel_integrations_hotel_id', 'hotel_integrations', ['hotel_id'], unique=False)


def downgrade() -> None:
    op.drop_table('hotel_integrations')
    op.drop_table('hotel_notifications')
    op.drop_table('hotel_themes')
    op.drop_table('hotel_configs')
