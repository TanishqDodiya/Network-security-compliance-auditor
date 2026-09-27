"""Shared PostgreSQL test-database helper (PostgreSQL only, no SQLite).

Tests require a DEDICATED PostgreSQL test database, isolated from the
development database::

    DATABASE_URL_TEST=postgresql+psycopg://postgres:PASSWORD@localhost:5432/network_security_auditor_test

Run from backend/ (venv activated)::

    python -m pytest tests/ -v

Rules:
- ``DATABASE_URL_TEST`` is required. If it is missing, DB-backed test
  modules skip with a clear message instead of touching the development
  database or falling back to SQLite.
- SQLite URLs are rejected outright.
- Each test module calls :func:`reset_test_schema` once at import, so every
  module starts from a clean schema (tables dropped + recreated). Tests
  inside one module keep sharing state exactly as before.
- The app itself (``app.database.session`` lifespan auto-seed) is pointed at
  the TEST database via ``DATABASE_URL`` default, unless the developer
  explicitly set ``DATABASE_URL`` already. Import this module BEFORE any
  ``app.*`` import so the environment is configured first.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_TEST_URL = (os.getenv("DATABASE_URL_TEST") or "").strip()

if not _TEST_URL:
    pytest.skip(
        "DATABASE_URL_TEST is required (PostgreSQL test database, isolated "
        "from development). Example: DATABASE_URL_TEST="
        "postgresql+psycopg://postgres:PASSWORD@localhost:5432"
        "/network_security_auditor_test",
        allow_module_level=True,
    )

if _TEST_URL.lower().startswith("sqlite"):
    raise RuntimeError("Tests must use PostgreSQL. SQLite is not supported.")

# Keep the FastAPI lifespan (init_db + rule auto-seed) off the dev database.
os.environ.setdefault("DATABASE_URL", _TEST_URL)


def _normalize(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


engine = create_engine(_normalize(_TEST_URL), pool_pre_ping=True, future=True)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def override_get_db():
    """FastAPI dependency override: sessions against the TEST database."""
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def reset_test_schema() -> None:
    """Drop + recreate all tables on the TEST database (clean slate)."""
    import app.models  # noqa: F401  (register tables on Base.metadata)
    from app.database.session import Base

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
