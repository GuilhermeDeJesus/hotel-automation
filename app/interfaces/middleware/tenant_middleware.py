"""Middleware de validação de tenant para multi-tenancy."""
from fastapi import HTTPException, Depends
from app.interfaces.dependencies.auth import get_current_user
from app.infrastructure.persistence.sql.models import UserModel


def validate_hotel_access(user: UserModel = Depends(get_current_user)):
    """
    Middleware que valida se o usuário tem acesso ao hotel especificado.
    Admin pode acessar todos os hotéis, outros usuários apenas o seu.
    """
    def _validate_hotel(resource_hotel_id: str) -> str:
        # Admin pode acessar qualquer hotel
        if user.role == "admin":
            return resource_hotel_id
        
        # Outros usuários só podem acessar seu próprio hotel
        if user.hotel_id != resource_hotel_id:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado: usuário não tem permissão para acessar dados do hotel {resource_hotel_id}"
            )
        
        return resource_hotel_id
    
    return _validate_hotel


def require_same_hotel(user: UserModel = Depends(get_current_user)):
    """
    Middleware que exige que o recurso seja do mesmo hotel do usuário.
    Mais restritivo que validate_hotel_access.
    """
    def _require_same_hotel(resource_hotel_id: str) -> str:
        if user.hotel_id != resource_hotel_id:
            raise HTTPException(
                status_code=403,
                detail=f"Acesso negado: recurso pertence a outro hotel"
            )
        
        return resource_hotel_id
    
    return _require_same_hotel


def get_user_hotel_id(user: UserModel = Depends(get_current_user)) -> str:
    """
    Retorna o hotel_id do usuário atual.
    Útil para filtrar dados automaticamente.
    """
    if not user.hotel_id:
        raise HTTPException(
            status_code=403,
            detail="Usuário não está associado a nenhum hotel"
        )
    
    return user.hotel_id


def hotel_or_admin(user: UserModel = Depends(get_current_user)):
    """
    Middleware que permite acesso se for admin ou do mesmo hotel.
    """
    def _check_access(resource_hotel_id: str) -> str:
        if user.role == "admin" or user.hotel_id == resource_hotel_id:
            return resource_hotel_id
        
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: permissão insuficiente"
        )
    
    return _check_access
