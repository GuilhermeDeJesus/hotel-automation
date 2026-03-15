from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.interfaces.api.auth import router as auth_router
from app.interfaces.api.hotel_dashboard import router as hotel_dashboard_router
from app.interfaces.api.hotel_settings import router as hotel_settings_router

app = FastAPI(title="Hotel Automation API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(hotel_dashboard_router)
app.include_router(hotel_settings_router)

@app.get("/")
def read_root():
    return {"message": "Hotel Automation API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}