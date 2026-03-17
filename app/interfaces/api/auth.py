from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.models import UserModel
from passlib.hash import bcrypt
import uuid
import jwt
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("auth")
logging.basicConfig(level=logging.WARNING)

router = APIRouter(prefix="/api/auth", tags=["auth"])

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_EXPIRE_MINUTES = 60

class RegisterRequest(BaseModel):
    email: str
    password: str
    hotel_id: str = None

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register", status_code=201)
def register_user(request: RegisterRequest):
    db: Session = SessionLocal()
    try:
        if db.query(UserModel).filter_by(email=request.email).first():
            raise HTTPException(status_code=400, detail="Email já registrado")

        user = UserModel(
            id=str(uuid.uuid4()),
            email=request.email,
            password_hash=bcrypt.hash(request.password),
            role="user",
            hotel_id=request.hotel_id,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(user)
        db.commit()
        return {"message": "Usuário registrado com sucesso"}
    finally:
        db.close()

@router.post("/login")
def login_user(request: LoginRequest):
    db: Session = SessionLocal()
    try:
        logger.warning(f"[LOGIN] Tentativa: email={request.email}")
        user = db.query(UserModel).filter_by(email=request.email).first()
        logger.warning(f"[LOGIN] Usuário encontrado: {user is not None}")

        if not user:
            logger.warning(f"[LOGIN] FALHA: usuário não encontrado para {request.email}")
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        logger.warning(f"[LOGIN] Hash: {user.password_hash[:20]}...")
        try:
            verified = bcrypt.verify(request.password, user.password_hash)
            logger.warning(f"[LOGIN] Senha verificada: {verified}")
        except Exception as e:
            logger.warning(f"[LOGIN] ERRO ao verificar senha: {e}")
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        if not verified:
            logger.warning(f"[LOGIN] FALHA: senha incorreta para {request.email}")
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        if not user.is_active:
            logger.warning(f"[LOGIN] FALHA: usuário inativo {request.email}")
            raise HTTPException(status_code=401, detail="Usuário inativo")

        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "hotel_id": user.hotel_id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        logger.warning(f"[LOGIN] SUCESSO para {request.email}")
        return {"token": token}
    finally:
        db.close()
