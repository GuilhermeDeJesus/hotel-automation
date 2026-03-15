from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from app.infrastructure.persistence.sql.models import UserModel
from app.infrastructure.persistence.sql.database import SessionLocal

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["sub"]
        db = SessionLocal()
        user = db.query(UserModel).filter_by(id=user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido ou inativo")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

def require_role(required_role: str):
    def _role_dependency(user: UserModel = Depends(get_current_user)):
        if user.role != required_role:
            raise HTTPException(status_code=403, detail=f"Permissão negada: requer {required_role}")
        return user
    return _role_dependency

def require_admin(user: UserModel = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Permissão negada: requer admin")
    return user

def require_manager(user: UserModel = Depends(get_current_user)):
    if user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Permissão negada: requer manager ou admin")
    return user

def require_staff(user: UserModel = Depends(get_current_user)):
    if user.role not in ["admin", "manager", "staff"]:
        raise HTTPException(status_code=403, detail="Permissão negada: requer staff, manager ou admin")
    return user
