"""Serviço para gerenciamento de configurações por Hotel."""
import json
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.infrastructure.persistence.sql.hotel_config_models import (
    HotelConfigModel, HotelThemeModel, HotelNotificationModel, HotelIntegrationModel
)
from app.infrastructure.persistence.sql.models import HotelModel, UserModel


class HotelConfigService:
    """Serviço para gerenciar configurações específicas do hotel."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_hotel_config(self, hotel_id: str, user: UserModel) -> HotelConfigModel:
        """Busca configurações do hotel com validação de permissão."""
        self._validate_hotel_access(hotel_id, user)
        
        config = self.session.query(HotelConfigModel).filter_by(hotel_id=hotel_id).first()
        
        if not config:
            # Criar configuração default
            hotel = self.session.query(HotelModel).filter_by(id=hotel_id).first()
            if not hotel:
                raise ValueError("Hotel não encontrado")
            
            config = HotelConfigModel(
                hotel_id=hotel_id,
                hotel_name=hotel.name,
                updated_by=user.id
            )
            self.session.add(config)
            self.session.flush()
        
        return config
    
    def update_hotel_config(
        self, 
        hotel_id: str, 
        config_data: Dict[str, Any], 
        user: UserModel
    ) -> HotelConfigModel:
        """Atualiza configurações do hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        config = self.get_hotel_config(hotel_id, user)
        
        # Atualizar campos permitidos
        updatable_fields = [
            'hotel_name', 'hotel_description', 'contact_email', 'contact_phone',
            'pix_key',
            'default_checkin_time', 'default_checkout_time', 'early_checkin_fee', 'late_checkout_fee',
            'cancellation_policy_hours', 'cancellation_fee_percentage', 'free_cancellation_hours',
            'requires_payment_for_confirmation', 'payment_methods', 'payment_deadline_hours',
            'max_guests_per_room', 'allows_extra_beds', 'extra_bed_fee',
            'child_policy', 'pet_policy', 'smoking_policy',
            'breakfast_included', 'breakfast_price', 'room_service_available', 'room_service_hours',
            'auto_send_confirmation', 'auto_send_reminder', 'reminder_hours_before',
            'whatsapp_enabled', 'whatsapp_number', 'whatsapp_business_hours',
            'rate_limit_config', 'audit_retention_days', 'audit_log_level',
            'currency', 'language', 'timezone',
            'theme', 'primary_color', 'logo_url',
            'active_integrations', 'webhook_urls',
            'auto_backup_enabled', 'backup_frequency_hours', 'backup_retention_days'
        ]
        
        for field in updatable_fields:
            if field in config_data:
                setattr(config, field, config_data[field])
        
        config.updated_by = user.id
        self.session.commit()
        
        return config
    
    def get_hotel_theme(self, hotel_id: str, user: UserModel) -> HotelThemeModel:
        """Busca tema personalizado do hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        theme = self.session.query(HotelThemeModel).filter_by(hotel_id=hotel_id).first()
        
        if not theme:
            # Criar tema default
            theme = HotelThemeModel(
                hotel_id=hotel_id,
                updated_by=user.id
            )
            self.session.add(theme)
            self.session.flush()
        
        return theme
    
    def update_hotel_theme(
        self, 
        hotel_id: str, 
        theme_data: Dict[str, Any], 
        user: UserModel
    ) -> HotelThemeModel:
        """Atualiza tema do hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        theme = self.get_hotel_theme(hotel_id, user)
        
        # Atualizar campos de tema
        theme_fields = [
            'primary_color', 'secondary_color', 'success_color', 'warning_color', 'danger_color', 'info_color',
            'body_bg_color', 'header_bg_color', 'sidebar_bg_color',
            'primary_text_color', 'secondary_text_color', 'muted_text_color',
            'font_family', 'font_size_base', 'font_weight_normal', 'font_weight_bold',
            'border_radius', 'border_width', 'border_color',
            'shadow_sm', 'shadow_md', 'shadow_lg',
            'container_max_width', 'sidebar_width', 'header_height',
            'enable_animations', 'animation_duration', 'animation_easing'
        ]
        
        for field in theme_fields:
            if field in theme_data:
                setattr(theme, field, theme_data[field])
        
        theme.updated_by = user.id
        self.session.commit()
        
        return theme
    
    def get_hotel_notifications(self, hotel_id: str, user: UserModel) -> HotelNotificationModel:
        """Busca configurações de notificação do hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        notifications = self.session.query(HotelNotificationModel).filter_by(hotel_id=hotel_id).first()
        
        if not notifications:
            # Criar configurações default
            notifications = HotelNotificationModel(
                hotel_id=hotel_id,
                updated_by=user.id
            )
            self.session.add(notifications)
            self.session.flush()
        
        return notifications
    
    def update_hotel_notifications(
        self, 
        hotel_id: str, 
        notification_data: Dict[str, Any], 
        user: UserModel
    ) -> HotelNotificationModel:
        """Atualiza configurações de notificação do hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        notifications = self.get_hotel_notifications(hotel_id, user)
        
        # Atualizar campos de notificação
        notification_fields = [
            'email_notifications_enabled', 'email_smtp_host', 'email_smtp_port', 
            'email_smtp_username', 'email_smtp_password', 'email_from_address', 'email_from_name',
            'email_on_new_reservation', 'email_on_payment_received', 'email_on_cancellation',
            'email_on_checkin', 'email_on_checkout',
            'sms_notifications_enabled', 'sms_provider', 'sms_api_key', 'sms_api_secret', 'sms_from_number',
            'sms_on_new_reservation', 'sms_on_payment_received', 'sms_on_cancellation', 'sms_on_checkin_reminder',
            'push_notifications_enabled', 'push_vapid_public_key', 'push_vapid_private_key', 'push_vapid_email',
            'push_on_new_message', 'push_on_reservation_update', 'push_on_payment_status',
            'whatsapp_notifications_enabled', 'whatsapp_business_api_token', 'whatsapp_phone_number_id',
            'whatsapp_on_new_reservation', 'whatsapp_on_payment_received', 'whatsapp_on_checkin_reminder', 'whatsapp_on_checkout_reminder',
            'notification_timezone', 'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            'max_notifications_per_hour', 'max_notifications_per_day'
        ]
        
        for field in notification_fields:
            if field in notification_data:
                setattr(notifications, field, notification_data[field])
        
        notifications.updated_by = user.id
        self.session.commit()
        
        return notifications
    
    def get_hotel_integrations(self, hotel_id: str, user: UserModel) -> List[HotelIntegrationModel]:
        """Busca integrações do hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        integrations = self.session.query(HotelIntegrationModel).filter_by(hotel_id=hotel_id).all()
        return integrations
    
    def create_hotel_integration(
        self, 
        hotel_id: str, 
        integration_data: Dict[str, Any], 
        user: UserModel
    ) -> HotelIntegrationModel:
        """Cria nova integração para o hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        integration = HotelIntegrationModel(
            hotel_id=hotel_id,
            integration_type=integration_data.get('integration_type'),
            integration_name=integration_data.get('integration_name'),
            config=integration_data.get('config'),
            api_credentials=integration_data.get('api_credentials'),
            sync_enabled=integration_data.get('sync_enabled', True),
            sync_frequency_minutes=integration_data.get('sync_frequency_minutes', 60),
            webhook_url=integration_data.get('webhook_url'),
            webhook_secret=integration_data.get('webhook_secret'),
            webhook_events=integration_data.get('webhook_events'),
            field_mapping=integration_data.get('field_mapping'),
            data_transformation_rules=integration_data.get('data_transformation_rules'),
            updated_by=user.id
        )
        
        self.session.add(integration)
        self.session.commit()
        
        return integration
    
    def update_hotel_integration(
        self, 
        hotel_id: str, 
        integration_id: str, 
        integration_data: Dict[str, Any], 
        user: UserModel
    ) -> HotelIntegrationModel:
        """Atualiza integração do hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        integration = self.session.query(HotelIntegrationModel).filter(
            and_(
                HotelIntegrationModel.hotel_id == hotel_id,
                HotelIntegrationModel.id == integration_id
            )
        ).first()
        
        if not integration:
            raise ValueError("Integração não encontrada")
        
        # Atualizar campos permitidos
        updatable_fields = [
            'is_active', 'config', 'api_credentials', 'sync_enabled', 'sync_frequency_minutes',
            'webhook_url', 'webhook_secret', 'webhook_events', 'field_mapping', 'data_transformation_rules'
        ]
        
        for field in updatable_fields:
            if field in integration_data:
                setattr(integration, field, integration_data[field])
        
        integration.updated_by = user.id
        self.session.commit()
        
        return integration
    
    def delete_hotel_integration(self, hotel_id: str, integration_id: str, user: UserModel):
        """Remove integração do hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        integration = self.session.query(HotelIntegrationModel).filter(
            and_(
                HotelIntegrationModel.hotel_id == hotel_id,
                HotelIntegrationModel.id == integration_id
            )
        ).first()
        
        if not integration:
            raise ValueError("Integração não encontrada")
        
        self.session.delete(integration)
        self.session.commit()
    
    def get_hotel_settings_summary(self, hotel_id: str, user: UserModel) -> Dict[str, Any]:
        """Retorna resumo de todas as configurações do hotel."""
        self._validate_hotel_access(hotel_id, user)
        
        config = self.get_hotel_config(hotel_id, user)
        theme = self.get_hotel_theme(hotel_id, user)
        notifications = self.get_hotel_notifications(hotel_id, user)
        integrations = self.get_hotel_integrations(hotel_id, user)
        
        return {
            "hotel_id": hotel_id,
            "hotel_name": config.hotel_name,
            "basic_config": {
                "contact_email": config.contact_email,
                "contact_phone": config.contact_phone,
                "currency": config.currency,
                "language": config.language,
                "timezone": config.timezone
            },
            "operational_config": {
                "checkin_time": config.default_checkin_time,
                "checkout_time": config.default_checkout_time,
                "requires_payment": config.requires_payment_for_confirmation,
                "whatsapp_enabled": config.whatsapp_enabled
            },
            "theme": {
                "primary_color": theme.primary_color,
                "theme": config.theme,
                "logo_url": config.logo_url
            },
            "notifications": {
                "email_enabled": notifications.email_notifications_enabled,
                "sms_enabled": notifications.sms_notifications_enabled,
                "whatsapp_enabled": notifications.whatsapp_notifications_enabled,
                "push_enabled": notifications.push_notifications_enabled
            },
            "integrations": {
                "total_count": len(integrations),
                "active_count": len([i for i in integrations if i.is_active]),
                "types": list(set([i.integration_type for i in integrations]))
            }
        }
    
    def reset_hotel_to_defaults(self, hotel_id: str, user: UserModel):
        """Reseta todas as configurações do hotel para os valores padrão."""
        self._validate_hotel_access(hotel_id, user)
        
        # Remover configurações existentes
        self.session.query(HotelConfigModel).filter_by(hotel_id=hotel_id).delete()
        self.session.query(HotelThemeModel).filter_by(hotel_id=hotel_id).delete()
        self.session.query(HotelNotificationModel).filter_by(hotel_id=hotel_id).delete()
        
        # Criar novas configurações default
        hotel = self.session.query(HotelModel).filter_by(id=hotel_id).first()
        if not hotel:
            raise ValueError("Hotel não encontrado")
        
        config = HotelConfigModel(
            hotel_id=hotel_id,
            hotel_name=hotel.name,
            updated_by=user.id
        )
        
        theme = HotelThemeModel(
            hotel_id=hotel_id,
            updated_by=user.id
        )
        
        notifications = HotelNotificationModel(
            hotel_id=hotel_id,
            updated_by=user.id
        )
        
        self.session.add_all([config, theme, notifications])
        self.session.commit()
    
    def _validate_hotel_access(self, hotel_id: str, user: UserModel):
        """Valida se usuário pode acessar configurações do hotel."""
        if user.role != "admin" and user.hotel_id != hotel_id:
            raise PermissionError(f"Usuário {user.email} não tem permissão para acessar configurações do hotel {hotel_id}")
