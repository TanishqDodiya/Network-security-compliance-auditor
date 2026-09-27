"""Database connection (PostgreSQL only).

PostgreSQL is the ONLY supported database. There is intentionally NO
SQLite support, NO local .db file, and NO silent fallback: if
``DATABASE_URL`` is missing or points at anything other than PostgreSQL,
the application fails fast with a clear error instead of running
against the wrong database.

Connection string (examples)::

    DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
    DATABASE_URL_TEST=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE_TEST

``postgres://`` / ``postgresql://`` scheme variants are normalized to the
``postgresql+psycopg://`` driver form automatically.

- Engine = the connection pool to PostgreSQL.
- SessionLocal = a helper that opens a short conversation with the database.
- Base = the parent class all our table models inherit from.
- get_db() = used by FastAPI APIs to get a database session (always closed).
- init_db() = creates all tables from models (safe to run many times).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

# Load .env if present. We check backend/.env then project-root .env.
# This never prints secrets, it only reads them.
_BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/
_PROJECT_ROOT = _BACKEND_DIR.parent  # network-security-auditor/
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_PROJECT_ROOT / ".env")


def _normalize_postgres_url(url: str) -> str:
    """Normalize scheme variants to the ``postgresql+psycopg://`` driver form."""
    # Heroku/Render style.
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    # Bare ``postgresql://`` without an explicit driver.
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _require_postgres_url(env_var: str = "DATABASE_URL") -> str:
    raw = (os.getenv(env_var) or "").strip()
    if not raw:
        raise RuntimeError(
            f"{env_var} is required. Example: "
            "DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE"
        )
    lowered = raw.lower()
    if lowered.startswith("sqlite"):
        raise RuntimeError(
            f"{env_var} must be a PostgreSQL URL. SQLite is not supported "
            "(no sqlite:// URLs, no .db files)."
        )
    url = _normalize_postgres_url(raw)
    if not url.lower().startswith(("postgresql+psycopg://", "postgres://", "postgresql://")):
        raise RuntimeError(
            f"{env_var} must be a PostgreSQL URL "
            "(postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE)."
        )
    return _normalize_postgres_url(url)


DATABASE_URL = _require_postgres_url("DATABASE_URL")

# Serverless (Vercel) functions must not hold pooled connections between
# invocations: one connection per request, closed afterwards.
_engine_kwargs: dict = {"pool_pre_ping": True, "future": True}
if os.getenv("VERCEL"):
    _engine_kwargs["poolclass"] = NullPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)
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
