"""Exemplos de uso do middleware de tenant validation."""

from fastapi import APIRouter, Depends
from app.interfaces.middleware.tenant_middleware import (
    validate_hotel_access, 
    require_same_hotel, 
    get_user_hotel_id,
    hotel_or_admin
)
from app.interfaces.dependencies.auth import get_current_user
from app.infrastructure.persistence.sql.models import UserModel

router = APIRouter()

# Exemplo 1: Endpoint que valida acesso ao hotel específico
@router.get("/hotels/{hotel_id}/rooms")
def list_hotel_rooms(
    hotel_id: str,
    user: UserModel = Depends(validate_hotel_access(hotel_id)),
    room_repo: RoomRepository = Depends(get_room_repository)
):
    """
    Lista quartos de um hotel específico.
    Admin pode ver qualquer hotel, usuários normais só o seu.
    """
    return room_repo.list_all(hotel_id)

# Exemplo 2: Endpoint que exige mesmo hotel do usuário
@router.post("/reservations")
def create_reservation(
    reservation_data: ReservationCreate,
    hotel_id: str = Depends(get_user_hotel_id),  # Pega hotel do usuário automaticamente
    user: UserModel = Depends(get_current_user),
    reservation_repo: ReservationRepository = Depends(get_reservation_repository)
):
    """
    Cria reserva no hotel do usuário automaticamente.
    Não precisa informar hotel_id no request body.
    """
    return reservation_repo.save(reservation_data, hotel_id)

# Exemplo 3: Endpoint com validação flexível (admin ou mesmo hotel)
@router.get("/reservations/{reservation_id}")
def get_reservation(
    reservation_id: str,
    user: UserModel = Depends(hotel_or_admin()),
    reservation_repo: ReservationRepository = Depends(get_reservation_repository)
):
    """
    Busca reserva específica.
    Admin pode ver qualquer, usuários só as do seu hotel.
    """
    reservation = reservation_repo.find_by_id(reservation_id, user.hotel_id)
    if not reservation:
        raise HTTPException(404, "Reserva não encontrada")
    
    # Validação adicional se não for admin
    if user.role != "admin" and reservation.hotel_id != user.hotel_id:
        raise HTTPException(403, "Acesso negado")
    
    return reservation

# Exemplo 4: Middleware em nível de rota
@router.get("/admin/dashboard")
def admin_dashboard(
    user: UserModel = Depends(require_same_hotel("target-hotel-id")),
    # Só permite acesso se for do mesmo hotel
):
    """
    Endpoint que só permite acesso do mesmo hotel.
    """
    return {"message": "Dashboard do hotel"}

# Exemplo 5: Uso em repositories
class ReservationService:
    def __init__(self, reservation_repo: ReservationRepository):
        self.reservation_repo = reservation_repo
    
    def list_user_reservations(
        self, 
        user: UserModel = Depends(get_current_user)
    ):
        """Lista apenas reservas do hotel do usuário."""
        return self.reservation_repo.list_reservations(
            hotel_id=user.hotel_id,
            from_date=None,
            to_date=None
        )
    
    def get_reservation_by_id(
        self, 
        reservation_id: str,
        user: UserModel = Depends(hotel_or_admin())
    ):
        """Busca reserva com validação de tenant."""
        reservation = self.reservation_repo.find_by_id(
            reservation_id, 
            user.hotel_id
        )
        
        if not reservation:
            raise HTTPException(404, "Reserva não encontrada")
        
        return reservation
