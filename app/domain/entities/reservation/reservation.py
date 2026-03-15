from datetime import date, datetime
from typing import Optional
from app.domain.value_objects.phone_number import PhoneNumber
from app.domain.entities.reservation.reservation_status import ReservationStatus
from app.domain.entities.reservation.stay_period import StayPeriod
from app.domain import exceptions


class Reservation:
    """
    Entidade de Domínio: Reservation
    
    Representa uma reserva de hotel com todas as regras de negócio.
    
    Regras:
    - Só pode fazer check-in se status = CONFIRMED ou PENDING
    - Só pode fazer check-out se já fez check-in
    - Reserva cancelada não pode mudar de estado
    - Check-in só é permitido no período correto
    """
    
    def __init__(
        self,
        reservation_id: str,
        guest_name: str,
        hotel_id: str,
        guest_phone: PhoneNumber,
        status: ReservationStatus,
        stay_period: Optional[StayPeriod] = None,
        room_number: Optional[str] = None,
        total_amount: Optional[float] = None,
        created_at: Optional[datetime] = None,
        checked_in_at: Optional[datetime] = None,
        checked_out_at: Optional[datetime] = None,
        guest_document: Optional[str] = None,
        estimated_arrival_time: Optional[str] = None,
        pre_checkin_completed_at: Optional[datetime] = None,
        digital_key_code: Optional[str] = None,
        consent_terms_accepted_at: Optional[datetime] = None,
        consent_marketing: bool = False,
    ):
        self.id = reservation_id
        self.guest_name = guest_name
        self.hotel_id = hotel_id
        self.guest_phone = guest_phone
        self.status = status
        self.stay_period = stay_period
        self.room_number = room_number
        self.total_amount = total_amount or 0.0
        self.created_at = created_at or datetime.now()
        self.checked_in_at = checked_in_at
        self.checked_out_at = checked_out_at
        self.guest_document = guest_document
        self.estimated_arrival_time = estimated_arrival_time
        self.pre_checkin_completed_at = pre_checkin_completed_at
        self.digital_key_code = digital_key_code
        self.consent_terms_accepted_at = consent_terms_accepted_at
        self.consent_marketing = consent_marketing
    
    def check_in(self, room_number: Optional[str] = None) -> None:
        """
        Realiza check-in do hóspede.
        
        Raises:
            InvalidCheckInState: Se status não permite check-in
            InvalidCheckInDate: Se data não permite check-in
        """
        # Valida status
        if self.status not in [ReservationStatus.CONFIRMED, ReservationStatus.PENDING]:
            raise exceptions.InvalidCheckInState(
                f"Só é possível fazer check-in em reservas confirmadas ou pendentes. Status atual: {self.status.name}"
            )
        
        # Valida se cancelada
        if self.status == ReservationStatus.CANCELLED:
            raise exceptions.InvalidCheckInState("Reserva cancelada não pode fazer check-in.")
        
        # Valida período (se definido)
        if self.stay_period and not self.stay_period.is_checkin_allowed(datetime.now().date()):
            raise exceptions.InvalidCheckInState(
                f"Check-in só permitido a partir de {self.stay_period.start}"
            )
        
        # Realiza check-in
        self.status = ReservationStatus.CHECKED_IN
        self.checked_in_at = datetime.now()
        if room_number:
            self.room_number = room_number
        # 6.4 Gera chave digital para self-check-in
        if not self.digital_key_code:
            import secrets
            self.digital_key_code = secrets.token_hex(4).upper()[:8]
    
    def check_out(self) -> None:
        """
        Realiza check-out do hóspede.
        
        Raises:
            InvalidCheckOutState: Se ainda não fez check-in
        """
        if self.status != ReservationStatus.CHECKED_IN:
            raise exceptions.InvalidCheckOutState(
                "Só é possível fazer check-out após check-in."
            )
        
        self.status = ReservationStatus.CHECKED_OUT
        self.checked_out_at = datetime.now()
    
    def cancel(self) -> None:
        """
        Cancela a reserva.
        
        Raises:
            InvalidCancellationState: Se já fez check-in ou check-out
        """
        if self.status in [ReservationStatus.CHECKED_IN, ReservationStatus.CHECKED_OUT]:
            raise exceptions.InvalidCancellationState(
                "Não é possível cancelar reserva após check-in."
            )
        
        self.status = ReservationStatus.CANCELLED
    
    def confirm(self) -> None:
        """Confirma uma reserva pendente."""
        if self.status == ReservationStatus.PENDING:
            self.status = ReservationStatus.CONFIRMED
    
    def mark_as_no_show(self) -> None:
        """Marca reserva como no-show (hóspede não compareceu)."""
        if self.status == ReservationStatus.CONFIRMED:
            self.status = ReservationStatus.NO_SHOW
    
    def is_active(self) -> bool:
        """Verifica se a reserva está ativa (não cancelada/finalizada)."""
        return self.status not in [
            ReservationStatus.CANCELLED, 
            ReservationStatus.CHECKED_OUT,
            ReservationStatus.NO_SHOW
        ]
    
    def can_checkin(self) -> bool:
        """Verifica se pode fazer check-in."""
        return self.status in [ReservationStatus.CONFIRMED, ReservationStatus.PENDING]

    def change_room(self, room_number: str) -> None:
        """
        Altera quarto da reserva. Só permitido antes do check-in.

        Raises:
            InvalidRoomChangeState: Se status não permite troca de quarto
        """
        if self.status not in (ReservationStatus.PENDING, ReservationStatus.CONFIRMED):
            raise exceptions.InvalidRoomChangeState(
                "Só é possível trocar quarto antes do check-in."
            )
        self.room_number = room_number

    def change_dates(self, new_period: StayPeriod, daily_rate: float) -> None:
        """
        Altera datas da reserva. Só permitido antes do check-in.

        Args:
            new_period: Novo período de estadia (validado pelo StayPeriod)
            daily_rate: Diária do quarto para recalcular total_amount

        Raises:
            InvalidDatesChangeState: Se status não permite alteração de datas
        """
        if self.status not in (ReservationStatus.PENDING, ReservationStatus.CONFIRMED):
            raise exceptions.InvalidDatesChangeState(
                "Só é possível alterar datas antes do check-in."
            )
        self.stay_period = new_period
        num_nights = new_period.number_of_nights()
        self.total_amount = daily_rate * num_nights

    def extend_stay(self, new_checkout: date, daily_rate: float) -> None:
        """
        Estende a estadia para nova data de check-out. Só permitido durante hospedagem.

        Args:
            new_checkout: Nova data de saída (deve ser > stay_period.end)
            daily_rate: Diária do quarto para recalcular total_amount

        Raises:
            InvalidExtendStayState: Se status não permite extensão
            InvalidExtendStayDate: Se new_checkout não é após o check-out atual
        """
        if self.status not in (ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN):
            raise exceptions.InvalidExtendStayState(
                "Só é possível estender estadia em reservas confirmadas ou com check-in realizado."
            )
        if not self.stay_period:
            raise exceptions.InvalidExtendStayDate("Reserva sem período definido.")
        if new_checkout <= self.stay_period.end:
            raise exceptions.InvalidExtendStayDate(
                f"A nova data de saída deve ser após {self.stay_period.end.strftime('%d/%m/%Y')}."
            )
        new_period = StayPeriod(
            self.stay_period.start, new_checkout, allow_past=True
        )
        self.stay_period = new_period
        num_nights = new_period.number_of_nights()
        self.total_amount = daily_rate * num_nights

    def complete_pre_checkin(
        self,
        guest_document: str,
        estimated_arrival_time: Optional[str] = None,
    ) -> None:
        """6.1 Check-in antecipado - registra documentos e horário estimado."""
        if self.status not in (ReservationStatus.PENDING, ReservationStatus.CONFIRMED):
            raise exceptions.InvalidCheckInState(
                "Pré-check-in só disponível para reservas pendentes ou confirmadas."
            )
        self.guest_document = guest_document
        self.estimated_arrival_time = estimated_arrival_time
        self.pre_checkin_completed_at = datetime.now()

    def accept_terms(self) -> None:
        """6.8 LGPD - aceita termos de uso."""
        self.consent_terms_accepted_at = datetime.now()

    def to_dict(self) -> dict:
        """Serializa a reserva para dicionário."""
        return {
            "id": self.id,
            "guest_name": self.guest_name,
            "hotel_id": self.hotel_id,
            "guest_phone": str(self.guest_phone),
            "status": self.status.name,
            "room_number": self.room_number,
            "total_amount": self.total_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "checked_in_at": self.checked_in_at.isoformat() if self.checked_in_at else None,
            "checked_out_at": self.checked_out_at.isoformat() if self.checked_out_at else None,
            "stay_period": {
                "start": self.stay_period.start.isoformat() if self.stay_period else None,
                "end": self.stay_period.end.isoformat() if self.stay_period else None
            } if self.stay_period else None
        }