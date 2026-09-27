"""Deploy readiness: /api/health, rule auto-seed helper, CORS origins.

Run from backend/ (venv activated):
    python -m pytest tests/test_deploy.py -v
"""

from fastapi.testclient import TestClient

from db_helper import TestingSession, override_get_db, reset_test_schema

from app.compliance.seed import ensure_demo_rules
from app.database.session import get_db
from app.main import app, cors_origins
from app.models.compliance_rule import ComplianceRule

app.dependency_overrides[get_db] = override_get_db
reset_test_schema()
client = TestClient(app)


def test_api_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


def test_ensure_demo_rules_idempotent():
    db = TestingSession()
    try:
        created, total = ensure_demo_rules(db)
        assert total == 10
        assert created == 10  # fresh in-memory DB
        created2, total2 = ensure_demo_rules(db)
        assert (created2, total2) == (0, 10)  # re-run changes nothing
        assert db.query(ComplianceRule).filter_by(rule_code="NET-001").count() == 1
    finally:
        db.close()


def test_cors_origins(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert "http://localhost:5173" in cors_origins()
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com, http://localhost:5173")
    origins = cors_origins()
    assert "https://app.example.com" in origins
    assert len(origins) == len(set(origins))  # no duplicates
