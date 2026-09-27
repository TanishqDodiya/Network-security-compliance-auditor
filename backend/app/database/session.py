"""Database connection for the MVP.

Simple idea:
- SQLite = a database stored in a single file (auditor.db). No server to install.
- SQLAlchemy = a Python library that lets us talk to the database using Python classes.
- Engine = the connection to the database file.
- SessionLocal = a helper that opens a short conversation with the database.
- Base = the parent class all our table models inherit from.
- get_db() = used later by FastAPI APIs to get a database session.
- init_db() = creates all tables from models (like building empty registers).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load .env if present. We check backend/.env then project-root .env.
# This never prints secrets, it only reads them.
_BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/
_PROJECT_ROOT = _BACKEND_DIR.parent  # network-security-auditor/
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auditor.db")

# SQLite needs this extra flag when used with FastAPI (multiple threads).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def get_db():
    """FastAPI dependency: open a session, give it to the API, then close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to run many times (won't delete data)."""
    # Import models here so they register themselves on Base.metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
