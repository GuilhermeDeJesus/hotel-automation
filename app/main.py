import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.interfaces.api.auth import router as auth_router

logger = logging.getLogger(__name__)
from app.interfaces.api.hotel_dashboard import router as hotel_dashboard_router
from app.interfaces.api.hotel_settings import router as hotel_settings_router

# Routers /saas
from app.interfaces.api.reservations import router as reservations_router
from app.interfaces.api.payments import router as payments_router
from app.interfaces.api.rooms import router as rooms_router
from app.interfaces.api.saas_dashboard import router as saas_dashboard_router
from app.interfaces.api.hotel_config import router as hotel_config_router
from app.interfaces.api.hotel_media import router as hotel_media_router
from app.interfaces.api.whatsapp_webhook import router as whatsapp_webhook_router

app = FastAPI(title="Hotel Automation API")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Loga erros não tratados e retorna 500 com CORS headers."""
    logger.exception("Erro não tratado em %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Verifique os logs."},
    )


# CORS - 5173 (vite dev), 4173 (vite preview), 5174 (dev alternativo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers

app.include_router(auth_router)
app.include_router(hotel_dashboard_router)
app.include_router(hotel_settings_router)
app.include_router(whatsapp_webhook_router)

# Incluir routers /saas
app.include_router(reservations_router)
app.include_router(payments_router)
app.include_router(rooms_router)
app.include_router(saas_dashboard_router)
app.include_router(hotel_config_router)
app.include_router(hotel_media_router)

@app.get("/")
def read_root():
    return {"message": "Hotel Automation API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}