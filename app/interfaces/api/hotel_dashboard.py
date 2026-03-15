"""Endpoints de Dashboard específicos por Hotel."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from app.interfaces.dependencies.auth import get_current_user
from app.infrastructure.persistence.sql.models import UserModel
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.models import (
    ReservationModel, RoomModel, CustomerModel, PaymentModel, 
    SupportTicketModel, RoomOrderModel, HotelModel
)


router = APIRouter(prefix="/dashboard/hotel", tags=["Hotel Dashboard"])


class DashboardStatsResponse(BaseModel):
    hotel_id: str
    hotel_name: str
    period_days: int
    total_reservations: int
    confirmed_reservations: int
    pending_reservations: int
    cancelled_reservations: int
    total_revenue: float
    occupancy_rate: float
    total_rooms: int
    occupied_rooms: int
    available_rooms: int
    maintenance_rooms: int
    total_customers: int
    new_customers_this_period: int
    total_payments: int
    successful_payments: int
    failed_payments: int
    total_support_tickets: int
    open_tickets: int
    resolved_tickets: int
    average_resolution_time_hours: float
    room_orders_count: int
    pending_orders: int
    completed_orders: int
    
    class Config:
        from_attributes = True


class RevenueAnalytics(BaseModel):
    daily_revenue: List[Dict[str, Any]]
    monthly_revenue: List[Dict[str, Any]]
    revenue_by_room_type: Dict[str, float]
    top_selling_rooms: List[Dict[str, Any]]
    payment_methods_breakdown: Dict[str, float]
    
    class Config:
        from_attributes = True


class OccupancyAnalytics(BaseModel):
    daily_occupancy: List[Dict[str, Any]]
    occupancy_by_room_type: Dict[str, float]
    peak_occupancy_days: List[Dict[str, Any]]
    low_occupancy_days: List[Dict[str, Any]]
    average_stay_duration: float
    
    class Config:
        from_attributes = True


class CustomerAnalytics(BaseModel):
    new_customers_trend: List[Dict[str, Any]]
    customer_distribution_by_source: Dict[str, int]
    repeat_customers: int
    customer_satisfaction_score: float
    top_customers_by_revenue: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


@router.get("/{hotel_id}/stats", response_model=DashboardStatsResponse)
def get_hotel_dashboard_stats(
    hotel_id: str,
    days: int = Query(30, le=365, ge=1),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retorna estatísticas completas do dashboard para um hotel específico.
    
    Apenas usuários do próprio hotel ou admins podem acessar.
    """
    # Validar permissão
    if current_user.role != "admin" and current_user.hotel_id != hotel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão negada para acessar dashboard deste hotel"
        )
    
    session = SessionLocal()
    try:
        # Obter informações do hotel
        hotel = session.query(HotelModel).filter_by(id=hotel_id).first()
        if not hotel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hotel não encontrado"
            )
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Estatísticas de Reservas
        total_reservations = session.query(ReservationModel).filter(
            and_(
                ReservationModel.hotel_id == hotel_id,
                ReservationModel.created_at >= start_date
            )
        ).count()
        
        confirmed_reservations = session.query(ReservationModel).filter(
            and_(
                ReservationModel.hotel_id == hotel_id,
                ReservationModel.created_at >= start_date,
                ReservationModel.status == "CONFIRMED"
            )
        ).count()
        
        pending_reservations = session.query(ReservationModel).filter(
            and_(
                ReservationModel.hotel_id == hotel_id,
                ReservationModel.created_at >= start_date,
                ReservationModel.status == "PENDING"
            )
        ).count()
        
        cancelled_reservations = session.query(ReservationModel).filter(
            and_(
                ReservationModel.hotel_id == hotel_id,
                ReservationModel.created_at >= start_date,
                ReservationModel.status == "CANCELLED"
            )
        ).count()
        
        # Estatísticas de Receita
        revenue_result = session.query(
            func.sum(PaymentModel.amount).label("total_revenue")
        ).filter(
            and_(
                PaymentModel.hotel_id == hotel_id,
                PaymentModel.created_at >= start_date,
                PaymentModel.status == "COMPLETED"
            )
        ).first()
        
        total_revenue = float(revenue_result.total_revenue or 0)
        
        # Estatísticas de Ocupação
        total_rooms = session.query(RoomModel).filter_by(hotel_id=hotel_id).count()
        occupied_rooms = session.query(ReservationModel).filter(
            and_(
                ReservationModel.hotel_id == hotel_id,
                ReservationModel.status == "CHECKED_IN"
            )
        ).count()
        
        available_rooms = session.query(RoomModel).filter(
            and_(
                RoomModel.hotel_id == hotel_id,
                RoomModel.status == "AVAILABLE"
            )
        ).count()
        
        maintenance_rooms = session.query(RoomModel).filter(
            and_(
                RoomModel.hotel_id == hotel_id,
                RoomModel.status == "MAINTENANCE"
            )
        ).count()
        
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        
        # Estatísticas de Clientes
        total_customers = session.query(CustomerModel).filter_by(hotel_id=hotel_id).count()
        new_customers = session.query(CustomerModel).filter(
            and_(
                CustomerModel.hotel_id == hotel_id,
                CustomerModel.created_at >= start_date
            )
        ).count()
        
        # Estatísticas de Pagamentos
        total_payments = session.query(PaymentModel).filter(
            and_(
                PaymentModel.hotel_id == hotel_id,
                PaymentModel.created_at >= start_date
            )
        ).count()
        
        successful_payments = session.query(PaymentModel).filter(
            and_(
                PaymentModel.hotel_id == hotel_id,
                PaymentModel.created_at >= start_date,
                PaymentModel.status == "COMPLETED"
            )
        ).count()
        
        failed_payments = total_payments - successful_payments
        
        # Estatísticas de Suporte
        total_tickets = session.query(SupportTicketModel).filter(
            and_(
                SupportTicketModel.hotel_id == hotel_id,
                SupportTicketModel.created_at >= start_date
            )
        ).count()
        
        open_tickets = session.query(SupportTicketModel).filter(
            and_(
                SupportTicketModel.hotel_id == hotel_id,
                SupportTicketModel.status == "OPEN"
            )
        ).count()
        
        resolved_tickets = session.query(SupportTicketModel).filter(
            and_(
                SupportTicketModel.hotel_id == hotel_id,
                SupportTicketModel.status == "CLOSED",
                SupportTicketModel.created_at >= start_date
            )
        ).count()
        
        # Tempo médio de resolução (simulado)
        average_resolution_time_hours = 24.5  # Implementar lógica real
        
        # Estatísticas de Pedidos de Quarto
        total_orders = session.query(RoomOrderModel).filter(
            and_(
                RoomOrderModel.hotel_id == hotel_id,
                RoomOrderModel.created_at >= start_date
            )
        ).count()
        
        pending_orders = session.query(RoomOrderModel).filter(
            and_(
                RoomOrderModel.hotel_id == hotel_id,
                RoomOrderModel.status == "PENDING"
            )
        ).count()
        
        completed_orders = session.query(RoomOrderModel).filter(
            and_(
                RoomOrderModel.hotel_id == hotel_id,
                RoomOrderModel.status == "COMPLETED"
            )
        ).count()
        
        return DashboardStatsResponse(
            hotel_id=hotel_id,
            hotel_name=hotel.name,
            period_days=days,
            total_reservations=total_reservations,
            confirmed_reservations=confirmed_reservations,
            pending_reservations=pending_reservations,
            cancelled_reservations=cancelled_reservations,
            total_revenue=total_revenue,
            occupancy_rate=occupancy_rate,
            total_rooms=total_rooms,
            occupied_rooms=occupied_rooms,
            available_rooms=available_rooms,
            maintenance_rooms=maintenance_rooms,
            total_customers=total_customers,
            new_customers_this_period=new_customers,
            total_payments=total_payments,
            successful_payments=successful_payments,
            failed_payments=failed_payments,
            total_support_tickets=total_tickets,
            open_tickets=open_tickets,
            resolved_tickets=resolved_tickets,
            average_resolution_time_hours=average_resolution_time_hours,
            room_orders_count=total_orders,
            pending_orders=pending_orders,
            completed_orders=completed_orders
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar estatísticas: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{hotel_id}/revenue-analytics", response_model=RevenueAnalytics)
def get_hotel_revenue_analytics(
    hotel_id: str,
    days: int = Query(30, le=365, ge=1),
    current_user: UserModel = Depends(get_current_user)
):
    """Retorna analytics de receita para um hotel."""
    # Validar permissão
    if current_user.role != "admin" and current_user.hotel_id != hotel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão negada"
        )
    
    session = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Receita diária
        daily_revenue = session.query(
            func.date(PaymentModel.created_at).label("date"),
            func.sum(PaymentModel.amount).label("revenue")
        ).filter(
            and_(
                PaymentModel.hotel_id == hotel_id,
                PaymentModel.created_at >= start_date,
                PaymentModel.status == "COMPLETED"
            )
        ).group_by(func.date(PaymentModel.created_at)).all()
        
        # Receita por tipo de quarto
        revenue_by_room_type = session.query(
            RoomModel.room_type,
            func.sum(PaymentModel.amount).label("revenue")
        ).join(
            ReservationModel, RoomModel.hotel_id == ReservationModel.hotel_id
        ).join(
            PaymentModel, ReservationModel.id == PaymentModel.reservation_id
        ).filter(
            and_(
                RoomModel.hotel_id == hotel_id,
                PaymentModel.created_at >= start_date,
                PaymentModel.status == "COMPLETED"
            )
        ).group_by(RoomModel.room_type).all()
        
        return RevenueAnalytics(
            daily_revenue=[{"date": str(r.date), "revenue": float(r.revenue)} for r in daily_revenue],
            monthly_revenue=[],  # Implementar lógica mensal
            revenue_by_room_type={r.room_type: float(r.revenue) for r in revenue_by_room_type},
            top_selling_rooms=[],  # Implementar lógica
            payment_methods_breakdown={}  # Implementar lógica
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar analytics de receita: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{hotel_id}/occupancy-analytics", response_model=OccupancyAnalytics)
def get_hotel_occupancy_analytics(
    hotel_id: str,
    days: int = Query(30, le=365, ge=1),
    current_user: UserModel = Depends(get_current_user)
):
    """Retorna analytics de ocupação para um hotel."""
    # Validar permissão
    if current_user.role != "admin" and current_user.hotel_id != hotel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão negada"
        )
    
    session = SessionLocal()
    try:
        # Implementar lógica de analytics de ocupação
        return OccupancyAnalytics(
            daily_occupancy=[],
            occupancy_by_room_type={},
            peak_occupancy_days=[],
            low_occupancy_days=[],
            average_stay_duration=2.5
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar analytics de ocupação: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{hotel_id}/customer-analytics", response_model=CustomerAnalytics)
def get_hotel_customer_analytics(
    hotel_id: str,
    days: int = Query(30, le=365, ge=1),
    current_user: UserModel = Depends(get_current_user)
):
    """Retorna analytics de clientes para um hotel."""
    # Validar permissão
    if current_user.role != "admin" and current_user.hotel_id != hotel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão negada"
        )
    
    session = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Novos clientes por dia
        new_customers_trend = session.query(
            func.date(CustomerModel.created_at).label("date"),
            func.count(CustomerModel.id).label("count")
        ).filter(
            and_(
                CustomerModel.hotel_id == hotel_id,
                CustomerModel.created_at >= start_date
            )
        ).group_by(func.date(CustomerModel.created_at)).all()
        
        return CustomerAnalytics(
            new_customers_trend=[{"date": str(r.date), "count": r.count} for r in new_customers_trend],
            customer_distribution_by_source={},  # Implementar
            repeat_customers=0,  # Implementar
            customer_satisfaction_score=4.5,  # Implementar
            top_customers_by_revenue=[]  # Implementar
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar analytics de clientes: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{hotel_id}/recent-activity")
def get_hotel_recent_activity(
    hotel_id: str,
    limit: int = Query(20, le=100),
    current_user: UserModel = Depends(get_current_user)
):
    """Retorna atividades recentes do hotel."""
    # Validar permissão
    if current_user.role != "admin" and current_user.hotel_id != hotel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão negada"
        )
    
    session = SessionLocal()
    try:
        activities = []
        
        # Reservas recentes
        recent_reservations = session.query(ReservationModel).filter(
            ReservationModel.hotel_id == hotel_id
        ).order_by(desc(ReservationModel.created_at)).limit(limit//4).all()
        
        for res in recent_reservations:
            activities.append({
                "type": "reservation",
                "id": res.id,
                "description": f"Reserva {res.status.lower()} - {res.guest_name}",
                "timestamp": res.created_at,
                "status": res.status
            })
        
        # Pagamentos recentes
        recent_payments = session.query(PaymentModel).filter(
            PaymentModel.hotel_id == hotel_id
        ).order_by(desc(PaymentModel.created_at)).limit(limit//4).all()
        
        for pay in recent_payments:
            activities.append({
                "type": "payment",
                "id": pay.id,
                "description": f"Pagamento {pay.status.lower()} - R$ {pay.amount:.2f}",
                "timestamp": pay.created_at,
                "status": pay.status
            })
        
        # Ordenar por timestamp
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "hotel_id": hotel_id,
            "activities": activities[:limit],
            "total_count": len(activities)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar atividades recentes: {str(e)}"
        )
    finally:
        session.close()


@router.get("/{hotel_id}/performance-metrics")
def get_hotel_performance_metrics(
    hotel_id: str,
    days: int = Query(30, le=365, ge=1),
    current_user: UserModel = Depends(get_current_user)
):
    """Retorna métricas de performance do hotel."""
    # Validar permissão
    if current_user.role != "admin" and current_user.hotel_id != hotel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão negada"
        )
    
    session = SessionLocal()
    try:
        # Implementar métricas de performance
        return {
            "hotel_id": hotel_id,
            "period_days": days,
            "metrics": {
                "average_response_time_minutes": 15.5,
                "customer_satisfaction_score": 4.3,
                "staff_performance_score": 4.7,
                "revenue_per_available_room": 250.75,
                "cost_per_occupied_room": 85.20,
                "gross_operating_profit_margin": 65.8
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar métricas de performance: {str(e)}"
        )
    finally:
        session.close()
