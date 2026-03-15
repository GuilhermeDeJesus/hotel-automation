from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.models import UserModel
from passlib.hash import bcrypt
import uuid
import jwt
import os
from datetime import datetime, timedelta

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
        user = db.query(UserModel).filter_by(email=request.email).first()
        if not user or not bcrypt.verify(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Credenciais inválidas")
        
        if not user.is_active:
            raise HTTPException(status_code=401, detail="Usuário inativo")
        
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "hotel_id": user.hotel_id,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        return {"token": token}
    finally:
        db.close()
