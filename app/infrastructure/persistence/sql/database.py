import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
# from dotenv import load_dotenv

# load environment variables from .env file if present
# load_dotenv()

# Padrão: Docker. DATABASE_URL deve apontar para host "db" (rede Docker).
# Use: docker compose up -d && make migrate
# tests may set TEST_DATABASE_URL to override the regular one
DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Padrão Docker: use 'make up' e 'make migrate' (ou carregue .env com load_dotenv)."
    )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Create database tables. Call once at startup or in setup scripts."""
    # Garante que hotel_configs e tabelas relacionadas sejam criadas
    import app.infrastructure.persistence.sql.hotel_config_models  # noqa: F401
    Base.metadata.create_all(bind=engine)
