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
    # Chave legada (sem hotel_id) - removida/ignorada para impedir skip cross-tenant.
    CHECKIN_DONE_KEY_PREFIX_LEGACY = "checkin_done:"

    def __init__(self, reservation_repository: ReservationRepository, cache_repository: CacheRepository):
        self.reservation_repository = reservation_repository
        self.cache_repository = cache_repository

    def execute(self, hotel_id: str, request_dto: CheckinRequestDTO) -> CheckinResponseDTO:
        phone = request_dto.phone_number
        cache_key = f"{self.CHECKIN_DONE_KEY_PREFIX}{hotel_id}:{phone}"
        legacy_cache_key = f"{self.CHECKIN_DONE_KEY_PREFIX_LEGACY}{phone}"

        # Segurança multi-tenant: não confiamos em chave legada sem hotel_id.
        # Se existir, removemos para impedir comportamento incorreto por TTL antigo.
        try:
            if self.cache_repository.get(legacy_cache_key):
                self.cache_repository.delete(legacy_cache_key)
        except Exception:
            # Falha ao apagar legado não deve bloquear o check-in.
            pass

        # Se já fez check-in (cache de resultado), retorna mensagem informativa
        if self.cache_repository.get(cache_key):
            # Ainda assim, tentamos montar a mensagem completa (quarto/chave),
            # pois melhora a UX quando a reserva já foi verificada anteriormente.
            reservation = self.reservation_repository.find_by_phone_number(phone, hotel_id)
            if reservation:
                room = getattr(reservation, "room_number", None) or ""
                digital_key = getattr(reservation, "digital_key_code", None) or ""
                if room and digital_key:
                    message = (
                        "Check-in feito com sucesso!\n"
                        f"Quarto: {room}\n"
                        f"Sua chave digital: {digital_key}\n"
                        "Boa estadia!"
                    )
                elif room:
                    message = (
                        "Check-in feito com sucesso!\n"
                        f"Quarto: {room}\n"
                        "Boa estadia!"
                    )
                else:
                    message = "Check-in feito com sucesso!\nBoa estadia!"

                return CheckinResponseDTO(message=message)

            return CheckinResponseDTO(message="Você já realizou o check-in.")

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

        room = getattr(reservation, "room_number", None) or ""
        digital_key = getattr(reservation, "digital_key_code", None) or ""
        if room and digital_key:
            message = (
                "Check-in feito com sucesso!\n"
                f"Quarto: {room}\n"
                f"Sua chave digital: {digital_key}\n"
                "Boa estadia!"
            )
        elif room:
            message = f"Check-in feito com sucesso!\nQuarto: {room}\nBoa estadia!"
        else:
            message = "Check-in feito com sucesso!\nBoa estadia!"

        return CheckinResponseDTO(message=message)