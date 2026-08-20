"""
Database connection and session management with SQLite fallback for offline development/testing.
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Database URL from environment variable, default to sqlite for self-contained offline testing
DEFAULT_DB_URL = "sqlite:///./offline_llm.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.warning(f"Failed to connect to primary DB {DATABASE_URL}: {e}. Falling back to SQLite.")
    engine = create_engine("sqlite:///./offline_llm.db", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency to get DB session with automatic creation of tables.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()