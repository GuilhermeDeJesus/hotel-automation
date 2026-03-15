import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
# from dotenv import load_dotenv

# load environment variables from .env file if present
# load_dotenv()

# allow configuring database URL via environment variable for flexibility
# tests may set TEST_DATABASE_URL to override the regular one
DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Create database tables. Call once at startup or in setup scripts."""
    Base.metadata.create_all(bind=engine)
