from sqlalchemy import Column, Integer, String, DateTime, Float, Date, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class RoomModel(Base):
    """Tabela de Quartos do Hotel"""
    __tablename__ = "rooms"

    id = Column(String, primary_key=True)
    number = Column(String(10), nullable=False, unique=True, index=True)
    room_type = Column(String(50), nullable=False)  # SINGLE, DOUBLE, SUITE
    daily_rate = Column(Float, nullable=False)
    max_guests = Column(Integer, default=2)
    status = Column(String(20), nullable=False, index=True, default="AVAILABLE")  # AVAILABLE, OCCUPIED, MAINTENANCE
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class CustomerModel(Base):
    """Tabela de Clientes/Hóspedes"""
    __tablename__ = "customers"

    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), index=True)
    email = Column(String(255), index=True)
    document = Column(String(20), unique=True)
    status = Column(String(20), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relacionamentos
    reservations = relationship("ReservationModel", back_populates="customer")


class ReservationModel(Base):
    """Tabela de Reservas"""
    __tablename__ = "reservations"

    id = Column(String, primary_key=True)
    
    # Dados do hóspede
    guest_name = Column(String(255), nullable=False)
    guest_phone = Column(String(20), index=True, nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=True)
    
    # Status e período
    status = Column(String(20), nullable=False, index=True)
    check_in_date = Column(Date)
    check_out_date = Column(Date)
    
    # Detalhes da estadia
    room_number = Column(String(10))
    total_amount = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    checked_in_at = Column(DateTime)
    checked_out_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Notas adicionais
    notes = Column(Text)

    # Relacionamentos
    customer = relationship("CustomerModel", back_populates="reservations")
    payments = relationship("PaymentModel", back_populates="reservation")


class PaymentModel(Base):
    """Tabela de Pagamentos"""
    __tablename__ = "payments"

    id = Column(String, primary_key=True)
    reservation_id = Column(String, ForeignKey("reservations.id"), nullable=False, index=True)
    
    # Dados do pagamento
    amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, index=True, default="PENDING")
    payment_method = Column(String(50))
    transaction_id = Column(String(255), unique=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    approved_at = Column(DateTime)
    expires_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relacionamentos
    reservation = relationship("ReservationModel", back_populates="payments")


class HotelModel(Base):
    """Tabela de Hotel (configuracoes e politicas)"""
    __tablename__ = "hotels"

    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    contact_phone = Column(String(30), nullable=False)
    checkin_time = Column(String(10), nullable=False)
    checkout_time = Column(String(10), nullable=False)
    cancellation_policy = Column(Text, nullable=False)
    pet_policy = Column(Text, nullable=False)
    child_policy = Column(Text, nullable=False)
    amenities = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ConversationCacheModel(Base):
    """Tabela de Cache de Conversas (WhatsApp)"""
    __tablename__ = "conversation_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(String(20), nullable=False, unique=True, index=True)
    context_data = Column(Text)  # JSON string
    last_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)