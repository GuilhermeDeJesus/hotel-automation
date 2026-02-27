from fastapi import FastAPI

from app.interfaces.api.whatsapp_webhook import router as whatsapp_router


app = FastAPI(title="Hotel Automation API")
app.include_router(whatsapp_router)