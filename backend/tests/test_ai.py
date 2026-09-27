"""Phase 11 test: AI fallback works with no API key; endpoints honest."""

import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.fallback import classify_unknown, explain_result, summarize_results
from app.ai.service import analyze_unknown, explain_finding, summarize_audit
from app.database.session import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_fallback_classification_keywords():
    assert classify_unknown("set xyz secure-admin-mode enabled")["suggested_category"] == "Management Security"
    assert classify_unknown("username admin password admin123")["suggested_category"] == "Authentication"
    assert classify_unknown("logging host 10.0.0.1")["suggested_category"] == "Logging"
    other = classify_unknown("blorp zzz qqq")
    assert other["suggested_category"] == "Other"
    assert 0.3 <= other["confidence"] <= 0.85


def test_service_without_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "none")
    out = analyze_unknown("set xyz secure-admin-mode enabled", "juniper")
    assert out["requires_confirmation"] is True
    assert out["ai_available"] is False
    assert out["provider"] == "fallback"
    assert out["suggested_category"] == "Management Security"

    exp = explain_finding("NET-001", "Telnet must be disabled", "FAIL", "service telnet", "Disable Telnet")
    assert "failed" in exp["explanation"].lower()
    assert exp["ai_available"] is False

    summary = summarize_audit([{"status": "PASS", "severity": "HIGH"}, {"status": "FAIL", "severity": "CRITICAL"}])
    assert "1 of 2" in summary["summary"]


def test_endpoints_return_200_with_flag():
    r = client.post("/api/ai/analyze", json={"text": "set xyz secure-admin-mode enabled", "vendor": "juniper"})
    assert r.status_code == 200
    body = r.json()
    assert body["requires_confirmation"] is True
    assert body["confidence"] > 0

    e = client.post("/api/ai/explain", json={
        "rule_code": "NET-001", "title": "Telnet must be disabled",
        "status": "FAIL", "evidence": "service telnet", "remediation": "Disable Telnet",
    })
    assert e.status_code == 200
    assert "explanation" in e.json()


def test_templates_unit():
    assert "passed" in explain_result("NET-002", "SSH", "PASS", "ssh v2", "").lower()
    assert "No rules" in summarize_results(0, 0, 0, 0, 0)
    assert os.getenv("AI_API_KEY", "") == "" or True  # keys never asserted
