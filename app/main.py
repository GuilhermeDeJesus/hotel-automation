import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.interfaces.api.whatsapp_webhook import router as whatsapp_router
from app.interfaces.api.saas_dashboard import router as saas_dashboard_router
from app.interfaces.api.payment_webhook import router as payment_webhook_router
from app.interfaces.api.reservations import router as reservations_router
from app.interfaces.api.payments import router as payments_router
from app.interfaces.api.hotel_config import router as hotel_config_router

app = FastAPI(title="Hotel Automation API")

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=([o.strip() for o in cors_origins if o.strip()]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router)
app.include_router(saas_dashboard_router)
app.include_router(payment_webhook_router)
app.include_router(reservations_router)
app.include_router(payments_router)
app.include_router(hotel_config_router)

@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}