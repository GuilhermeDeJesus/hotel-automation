"""
Check-in via WhatsApp Use Case - orchestrates guest check-in.

Cache de resultado: usa chave checkin_done:{phone} para evitar repetição.
Só grava após check-in bem-sucedido; nunca retorna sucesso sem executar.
"""
from app.application.dto.checkin_request_dto import CheckinRequestDTO
from app.application.dto.checkin_response_dto import CheckinResponseDTO
from app.domain import exceptions
from app.domain.repositories.cache_repository import CacheRepository
from app.domain.repositories.reservation_repository import ReservationRepository


class CheckInViaWhatsAppUseCase:
    """Orquestra o check-in do hóspede via WhatsApp."""

    CHECKIN_DONE_KEY_PREFIX = "checkin_done:"
    CHECKIN_DONE_TTL_SECONDS = 86400  # 24h

    def __init__(self, reservation_repository: ReservationRepository, cache_repository: CacheRepository):
        self.reservation_repository = reservation_repository
        self.cache_repository = cache_repository

    def execute(self, hotel_id: str, request_dto: CheckinRequestDTO) -> CheckinResponseDTO:
        phone = request_dto.phone_number
        cache_key = f"{self.CHECKIN_DONE_KEY_PREFIX}{phone}"

        # Se já fez check-in (cache de resultado), retorna mensagem informativa
        if self.cache_repository.get(cache_key):
            return CheckinResponseDTO(
                message="Você já realizou o check-in."
            )

        # Busca reserva no repositório
        reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
        if not reservation:
            return CheckinResponseDTO(
                message="Nenhuma reserva encontrada para esse numero."
            )

        # Executa check-in (domínio) e persiste
        try:
            reservation.check_in()
            self.reservation_repository.save(reservation, hotel_id)
        except (exceptions.InvalidCheckInState, exceptions.InvalidCheckInDate) as e:
            return CheckinResponseDTO(
                message=str(e),
                success=False,
                error=str(e),
            )

        # Grava cache de resultado APÓS check-in bem-sucedido
        self.cache_repository.set(cache_key, {"done": True}, ttl_seconds=self.CHECKIN_DONE_TTL_SECONDS)

        return CheckinResponseDTO(
            message="Check-in feito com sucesso!"
        )