"""Endpoints de configurações específicas por Hotel."""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

from app.interfaces.dependencies.auth import get_current_user
from app.infrastructure.persistence.sql.models import UserModel
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.hotel_config_repository import HotelConfigService


router = APIRouter(prefix="/config/hotel", tags=["Hotel Configuration"])

# Pydantic models
class HotelConfigRequest(BaseModel):
    hotel_name: Optional[str] = None
    hotel_description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    pix_key: Optional[str] = None
    default_checkin_time: Optional[str] = None
    default_checkout_time: Optional[str] = None
    early_checkin_fee: Optional[float] = None
    late_checkout_fee: Optional[float] = None
    cancellation_policy_hours: Optional[int] = None
    cancellation_fee_percentage: Optional[float] = None
    free_cancellation_hours: Optional[int] = None
    requires_payment_for_confirmation: Optional[bool] = None
    payment_methods: Optional[List[str]] = None
    payment_deadline_hours: Optional[int] = None
    max_guests_per_room: Optional[int] = None
    allows_extra_beds: Optional[bool] = None
    extra_bed_fee: Optional[float] = None
    child_policy: Optional[str] = None
    pet_policy: Optional[str] = None
    smoking_policy: Optional[str] = None
    breakfast_included: Optional[bool] = None
    breakfast_price: Optional[float] = None
    room_service_available: Optional[bool] = None
    room_service_hours: Optional[Dict[str, str]] = None
    auto_send_confirmation: Optional[bool] = None
    auto_send_reminder: Optional[bool] = None
    reminder_hours_before: Optional[int] = None
    whatsapp_enabled: Optional[bool] = None
    whatsapp_number: Optional[str] = None
    whatsapp_business_hours: Optional[Dict[str, str]] = None
    rate_limit_config: Optional[Dict[str, Any]] = None
    audit_retention_days: Optional[int] = None
    audit_log_level: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    theme: Optional[str] = None
    primary_color: Optional[str] = None
    logo_url: Optional[str] = None
    active_integrations: Optional[Dict[str, bool]] = None
    webhook_urls: Optional[Dict[str, str]] = None
    auto_backup_enabled: Optional[bool] = None
    backup_frequency_hours: Optional[int] = None
    backup_retention_days: Optional[int] = None


class HotelThemeRequest(BaseModel):
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    success_color: Optional[str] = None
    warning_color: Optional[str] = None
    danger_color: Optional[str] = None
    info_color: Optional[str] = None
    body_bg_color: Optional[str] = None
    header_bg_color: Optional[str] = None
    sidebar_bg_color: Optional[str] = None
    primary_text_color: Optional[str] = None
    secondary_text_color: Optional[str] = None
    muted_text_color: Optional[str] = None
    font_family: Optional[str] = None
    font_size_base: Optional[str] = None
    font_weight_normal: Optional[str] = None
    font_weight_bold: Optional[str] = None
    border_radius: Optional[str] = None
    border_width: Optional[str] = None
    border_color: Optional[str] = None
    shadow_sm: Optional[str] = None
    shadow_md: Optional[str] = None
    shadow_lg: Optional[str] = None
    container_max_width: Optional[str] = None
    sidebar_width: Optional[str] = None
    header_height: Optional[str] = None
    enable_animations: Optional[bool] = None
    animation_duration: Optional[str] = None
    animation_easing: Optional[str] = None


class HotelNotificationRequest(BaseModel):
    email_notifications_enabled: Optional[bool] = None
    email_smtp_host: Optional[str] = None
    email_smtp_port: Optional[int] = None
    email_smtp_username: Optional[str] = None
    email_smtp_password: Optional[str] = None
    email_from_address: Optional[str] = None
    email_from_name: Optional[str] = None
    email_on_new_reservation: Optional[bool] = None
    email_on_payment_received: Optional[bool] = None
    email_on_cancellation: Optional[bool] = None
    email_on_checkin: Optional[bool] = None
    email_on_checkout: Optional[bool] = None
    sms_notifications_enabled: Optional[bool] = None
    sms_provider: Optional[str] = None
    sms_api_key: Optional[str] = None
    sms_api_secret: Optional[str] = None
    sms_from_number: Optional[str] = None
    sms_on_new_reservation: Optional[bool] = None
    sms_on_payment_received: Optional[bool] = None
    sms_on_cancellation: Optional[bool] = None
    sms_on_checkin_reminder: Optional[bool] = None
    push_notifications_enabled: Optional[bool] = None
    push_vapid_public_key: Optional[str] = None
    push_vapid_private_key: Optional[str] = None
    push_vapid_email: Optional[str] = None
    push_on_new_message: Optional[bool] = None
    push_on_reservation_update: Optional[bool] = None
    push_on_payment_status: Optional[bool] = None
    whatsapp_notifications_enabled: Optional[bool] = None
    whatsapp_business_api_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_on_new_reservation: Optional[bool] = None
    whatsapp_on_payment_received: Optional[bool] = None
    whatsapp_on_checkin_reminder: Optional[bool] = None
    whatsapp_on_checkout_reminder: Optional[bool] = None
    notification_timezone: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    max_notifications_per_hour: Optional[int] = None
    max_notifications_per_day: Optional[int] = None


class HotelIntegrationRequest(BaseModel):
    integration_type: str
    integration_name: str
    config: Optional[Dict[str, Any]] = None
    api_credentials: Optional[Dict[str, str]] = None
    sync_enabled: Optional[bool] = True
    sync_frequency_minutes: Optional[int] = 60
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_events: Optional[List[str]] = None
    field_mapping: Optional[Dict[str, str]] = None
    data_transformation_rules: Optional[Dict[str, Any]] = None


@router.get("/{hotel_id}/config")
def get_hotel_config(
    hotel_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Busca configurações completas do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        config = config_service.get_hotel_config(hotel_id, current_user)
        
        return {
            "hotel_id": config.hotel_id,
            "hotel_name": config.hotel_name,
            "hotel_description": config.hotel_description,
            "contact_email": config.contact_email,
            "contact_phone": config.contact_phone,
            "pix_key": config.pix_key,
            "default_checkin_time": config.default_checkin_time,
            "default_checkout_time": config.default_checkout_time,
            "early_checkin_fee": config.early_checkin_fee,
            "late_checkout_fee": config.late_checkout_fee,
            "cancellation_policy_hours": config.cancellation_policy_hours,
            "cancellation_fee_percentage": config.cancellation_fee_percentage,
            "free_cancellation_hours": config.free_cancellation_hours,
            "requires_payment_for_confirmation": config.requires_payment_for_confirmation,
            "payment_methods": config.payment_methods,
            "payment_deadline_hours": config.payment_deadline_hours,
            "max_guests_per_room": config.max_guests_per_room,
            "allows_extra_beds": config.allows_extra_beds,
            "extra_bed_fee": config.extra_bed_fee,
            "child_policy": config.child_policy,
            "pet_policy": config.pet_policy,
            "smoking_policy": config.smoking_policy,
            "breakfast_included": config.breakfast_included,
            "breakfast_price": config.breakfast_price,
            "room_service_available": config.room_service_available,
            "room_service_hours": config.room_service_hours,
            "auto_send_confirmation": config.auto_send_confirmation,
            "auto_send_reminder": config.auto_send_reminder,
            "reminder_hours_before": config.reminder_hours_before,
            "whatsapp_enabled": config.whatsapp_enabled,
            "whatsapp_number": config.whatsapp_number,
            "whatsapp_business_hours": config.whatsapp_business_hours,
            "rate_limit_config": config.rate_limit_config,
            "audit_retention_days": config.audit_retention_days,
            "audit_log_level": config.audit_log_level,
            "currency": config.currency,
            "language": config.language,
            "timezone": config.timezone,
            "theme": config.theme,
            "primary_color": config.primary_color,
            "logo_url": config.logo_url,
            "active_integrations": config.active_integrations,
            "webhook_urls": config.webhook_urls,
            "auto_backup_enabled": config.auto_backup_enabled,
            "backup_frequency_hours": config.backup_frequency_hours,
            "backup_retention_days": config.backup_retention_days,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar configurações: {str(e)}"
        )
    finally:
        session.close()


@router.put("/{hotel_id}/config")
def update_hotel_config(
    hotel_id: str,
    config_data: HotelConfigRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Atualiza configurações do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        
        # Converter Pydantic model para dict
        config_dict = config_data.dict(exclude_unset=True)
        
        config = config_service.update_hotel_config(hotel_id, config_dict, current_user)
        
        return {
            "message": "Configurações atualizadas com sucesso",
            "hotel_id": config.hotel_id,
            "updated_at": config.updated_at
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar configurações: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{hotel_id}/theme")
def get_hotel_theme(
    hotel_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Busca tema personalizado do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        theme = config_service.get_hotel_theme(hotel_id, current_user)
        
        return {
            "hotel_id": theme.hotel_id,
            "primary_color": theme.primary_color,
            "secondary_color": theme.secondary_color,
            "success_color": theme.success_color,
            "warning_color": theme.warning_color,
            "danger_color": theme.danger_color,
            "info_color": theme.info_color,
            "body_bg_color": theme.body_bg_color,
            "header_bg_color": theme.header_bg_color,
            "sidebar_bg_color": theme.sidebar_bg_color,
            "primary_text_color": theme.primary_text_color,
            "secondary_text_color": theme.secondary_text_color,
            "muted_text_color": theme.muted_text_color,
            "font_family": theme.font_family,
            "font_size_base": theme.font_size_base,
            "font_weight_normal": theme.font_weight_normal,
            "font_weight_bold": theme.font_weight_bold,
            "border_radius": theme.border_radius,
            "border_width": theme.border_width,
            "border_color": theme.border_color,
            "shadow_sm": theme.shadow_sm,
            "shadow_md": theme.shadow_md,
            "shadow_lg": theme.shadow_lg,
            "container_max_width": theme.container_max_width,
            "sidebar_width": theme.sidebar_width,
            "header_height": theme.header_height,
            "enable_animations": theme.enable_animations,
            "animation_duration": theme.animation_duration,
            "animation_easing": theme.animation_easing
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar tema: {str(e)}"
        )
    finally:
        session.close()


@router.put("/{hotel_id}/theme")
def update_hotel_theme(
    hotel_id: str,
    theme_data: HotelThemeRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Atualiza tema do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        
        # Converter Pydantic model para dict
        theme_dict = theme_data.dict(exclude_unset=True)
        
        theme = config_service.update_hotel_theme(hotel_id, theme_dict, current_user)
        
        return {
            "message": "Tema atualizado com sucesso",
            "hotel_id": theme.hotel_id,
            "updated_at": theme.updated_at
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar tema: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{hotel_id}/notifications")
def get_hotel_notifications(
    hotel_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Busca configurações de notificação do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        notifications = config_service.get_hotel_notifications(hotel_id, current_user)
        
        return {
            "hotel_id": notifications.hotel_id,
            "email_notifications_enabled": notifications.email_notifications_enabled,
            "email_smtp_host": notifications.email_smtp_host,
            "email_smtp_port": notifications.email_smtp_port,
            "email_smtp_username": notifications.email_smtp_username,
            "email_from_address": notifications.email_from_address,
            "email_from_name": notifications.email_from_name,
            "email_on_new_reservation": notifications.email_on_new_reservation,
            "email_on_payment_received": notifications.email_on_payment_received,
            "email_on_cancellation": notifications.email_on_cancellation,
            "email_on_checkin": notifications.email_on_checkin,
            "email_on_checkout": notifications.email_on_checkout,
            "sms_notifications_enabled": notifications.sms_notifications_enabled,
            "sms_provider": notifications.sms_provider,
            "sms_from_number": notifications.sms_from_number,
            "sms_on_new_reservation": notifications.sms_on_new_reservation,
            "sms_on_payment_received": notifications.sms_on_payment_received,
            "sms_on_cancellation": notifications.sms_on_cancellation,
            "sms_on_checkin_reminder": notifications.sms_on_checkin_reminder,
            "push_notifications_enabled": notifications.push_notifications_enabled,
            "push_on_new_message": notifications.push_on_new_message,
            "push_on_reservation_update": notifications.push_on_reservation_update,
            "push_on_payment_status": notifications.push_on_payment_status,
            "whatsapp_notifications_enabled": notifications.whatsapp_notifications_enabled,
            "whatsapp_on_new_reservation": notifications.whatsapp_on_new_reservation,
            "whatsapp_on_payment_received": notifications.whatsapp_on_payment_received,
            "whatsapp_on_checkin_reminder": notifications.whatsapp_on_checkin_reminder,
            "whatsapp_on_checkout_reminder": notifications.whatsapp_on_checkout_reminder,
            "notification_timezone": notifications.notification_timezone,
            "quiet_hours_enabled": notifications.quiet_hours_enabled,
            "quiet_hours_start": notifications.quiet_hours_start,
            "quiet_hours_end": notifications.quiet_hours_end,
            "max_notifications_per_hour": notifications.max_notifications_per_hour,
            "max_notifications_per_day": notifications.max_notifications_per_day
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar configurações de notificação: {str(e)}"
        )
    finally:
        session.close()


@router.put("/{hotel_id}/notifications")
def update_hotel_notifications(
    hotel_id: str,
    notification_data: HotelNotificationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Atualiza configurações de notificação do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        
        # Converter Pydantic model para dict
        notification_dict = notification_data.dict(exclude_unset=True)
        
        notifications = config_service.update_hotel_notifications(hotel_id, notification_dict, current_user)
        
        return {
            "message": "Configurações de notificação atualizadas com sucesso",
            "hotel_id": notifications.hotel_id,
            "updated_at": notifications.updated_at
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar configurações de notificação: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{hotel_id}/integrations")
def get_hotel_integrations(
    hotel_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Busca integrações do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        integrations = config_service.get_hotel_integrations(hotel_id, current_user)
        
        return {
            "hotel_id": hotel_id,
            "integrations": [
                {
                    "id": integration.id,
                    "integration_type": integration.integration_type,
                    "integration_name": integration.integration_name,
                    "is_active": integration.is_active,
                    "sync_enabled": integration.sync_enabled,
                    "sync_frequency_minutes": integration.sync_frequency_minutes,
                    "last_sync_at": integration.last_sync_at,
                    "sync_status": integration.sync_status,
                    "total_syncs": integration.total_syncs,
                    "successful_syncs": integration.successful_syncs,
                    "failed_syncs": integration.failed_syncs,
                    "last_error_message": integration.last_error_message,
                    "created_at": integration.created_at,
                    "updated_at": integration.updated_at
                }
                for integration in integrations
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar integrações: {str(e)}"
        )
    finally:
        session.close()


@router.post("/{hotel_id}/integrations")
def create_hotel_integration(
    hotel_id: str,
    integration_data: HotelIntegrationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Cria nova integração para o hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        
        # Converter Pydantic model para dict
        integration_dict = integration_data.dict()
        
        integration = config_service.create_hotel_integration(hotel_id, integration_dict, current_user)
        
        return {
            "message": "Integração criada com sucesso",
            "integration_id": integration.id,
            "integration_type": integration.integration_type,
            "integration_name": integration.integration_name,
            "created_at": integration.created_at
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar integração: {str(e)}"
        )
    finally:
        session.close()


@router.put("/{hotel_id}/integrations/{integration_id}")
def update_hotel_integration(
    hotel_id: str,
    integration_id: str,
    integration_data: HotelIntegrationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Atualiza integração do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        
        # Converter Pydantic model para dict
        integration_dict = integration_data.dict(exclude_unset=True)
        
        integration = config_service.update_hotel_integration(hotel_id, integration_id, integration_dict, current_user)
        
        return {
            "message": "Integração atualizada com sucesso",
            "integration_id": integration.id,
            "updated_at": integration.updated_at
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar integração: {str(e)}"
        )
    finally:
        session.close()


@router.delete("/{hotel_id}/integrations/{integration_id}")
def delete_hotel_integration(
    hotel_id: str,
    integration_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Remove integração do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        config_service.delete_hotel_integration(hotel_id, integration_id, current_user)
        
        return {
            "message": "Integração removida com sucesso",
            "integration_id": integration_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover integração: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{hotel_id}/summary")
def get_hotel_settings_summary(
    hotel_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Retorna resumo de todas as configurações do hotel."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        summary = config_service.get_hotel_settings_summary(hotel_id, current_user)
        
        return summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar resumo das configurações: {str(e)}"
        )
    finally:
        session.close()


@router.post("/{hotel_id}/reset")
def reset_hotel_to_defaults(
    hotel_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Reseta todas as configurações do hotel para os valores padrão."""
    session = SessionLocal()
    try:
        config_service = HotelConfigService(session)
        config_service.reset_hotel_to_defaults(hotel_id, current_user)
        
        return {
            "message": "Configurações resetadas para os valores padrão com sucesso",
            "hotel_id": hotel_id,
            "reset_by": current_user.email
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao resetar configurações: {str(e)}"
        )
    finally:
        session.close()
