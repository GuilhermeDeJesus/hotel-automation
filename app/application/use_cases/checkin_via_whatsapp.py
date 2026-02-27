from app.application.dto.checkin_request_dto import CheckinRequestDTO
from app.application.dto.checkin_response_dto import CheckinResponseDTO
from app.domain.repositories.cache_repository import CacheRepository
from app.domain.repositories.reservation_repository import ReservationRepository

# Orquestração
class CheckInViaWhatsAppUseCase:
    def __init__(self, reservation_repository: ReservationRepository, cache_repository: CacheRepository):
        self.reservation_repository = reservation_repository
        self.cache_repository = cache_repository
    
    # O ponto: CheckInViaWhatsAppUseCase espera um ReservationRepository, não especificamente um ReservationRepositorySQL. Se amanhã você quiser trocar para MongoDB, cria ReservationRepositoryMongo, e o use-case continua funcionando sem mudança.
    def execute(self, request_dto: CheckinRequestDTO) -> CheckinResponseDTO:
        # ✅ ORQUESTRA: Verifica cache primeiro?
        # Verificar se a reserva está no cache
        cached_reservation = self.cache_repository.get(request_dto.phone_number)
        if cached_reservation:
            return CheckinResponseDTO(
                message="Reserva encontrada no cache. Check-in feito com sucesso!"
            )
            
         # ✅ ORQUESTRA: Se não tiver cache, busca no banco
        # Se não estiver no cache, consultar o repositório de reservas
        reservation = self.reservation_repository.find_by_phone_number(request_dto.phone_number)
        
        if not reservation:
            return CheckinResponseDTO(
                message="Nenhuma reserva encontrada para esse numero."
            )
            
        reservation.check_in()
        self.reservation_repository.save(reservation)
        
        # Armazenar a informação da reserva no cache do Redis (usar representação serializável)
        try:
            data = reservation.to_dict()
        except Exception:
            data = {
                "id": reservation.id,
                "guest_phone": str(reservation.guest_phone),
                "status": getattr(reservation.status, 'name', str(reservation.status))
            }
        self.cache_repository.set(request_dto.phone_number, data)
        
        return CheckinResponseDTO(
            message="Check-in feito com sucesso!"
        )