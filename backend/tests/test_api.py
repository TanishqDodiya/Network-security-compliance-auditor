"""Phase 3 test: REST APIs with an isolated in-memory database.

Run from backend/ (venv activated):
    python -m pytest tests/test_api.py -v
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import app

# One shared in-memory DB for the whole test (StaticPool keeps single connection).
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


def test_devices_crud():
    r = client.post("/api/devices", json={"name": "Cisco-Router-01", "vendor": "cisco"})
    assert r.status_code == 201, r.text
    device_id = r.json()["id"]

    dup = client.post("/api/devices", json={"name": "Cisco-Router-01"})
    assert dup.status_code == 409

    assert client.get("/api/devices").status_code == 200
    assert client.get(f"/api/devices/{device_id}").status_code == 200
    assert client.get("/api/devices/9999").status_code == 404


def test_upload_validation_and_list():
    good = client.post(
        "/api/configurations/upload",
        files={"config": ("router.conf", b"hostname R1\n", "text/plain")},
        data={"device_name": "Cisco-Router-01"},
    )
    # NOTE: field name must be "file"; wrong name -> 422 (proves validation works).
    assert good.status_code == 422

    good = client.post(
        "/api/configurations/upload",
        files={"file": ("router.conf", b"hostname R1\n", "text/plain")},
    )
    assert good.status_code == 201, good.text
    body = good.json()
    # Single "hostname" line scores 1 (< threshold 2) so honestly stays "unknown".
    assert body["detected_vendor"] == "unknown"
    assert body["status"] == "Ready for Audit"
    config_id = body["configuration_id"]

    bad_ext = client.post(
        "/api/configurations/upload",
        files={"file": ("evil.exe", b"data", "application/octet-stream")},
    )
    assert bad_ext.status_code == 400

    empty = client.post(
        "/api/configurations/upload",
        files={"file": ("empty.conf", b"", "text/plain")},
    )
    assert empty.status_code == 400

    assert client.get("/api/configurations").status_code == 200
    assert config_id > 0


def test_rules_audits_results():
    r = client.post(
        "/api/rules",
        json={
            "rule_code": "NET-001",
            "title": "Telnet must be disabled",
            "category": "Secure Management",
            "severity": "HIGH",
            "framework": ["Demo Security Rule"],
            "field": "management.telnet_enabled",
            "expected": False,
            "description": "Telnet transmits credentials without adequate protection.",
            "remediation": "Disable Telnet and use SSH.",
        },
    )
    assert r.status_code == 201, r.text
    assert client.post(
        "/api/rules",
        json={"rule_code": "NET-001", "title": "dup", "field": "x", "expected": True},
    ).status_code == 409
    assert client.get("/api/rules").status_code == 200

    # Need a configuration to audit.
    up = client.post(
        "/api/configurations/upload",
        files={"file": ("audit-me.conf", b"hostname X", "text/plain")},
    )
    config_id = up.json()["configuration_id"]

    audit = client.post("/api/audits", json={"configuration_id": config_id})
    assert audit.status_code == 201, audit.text
    audit_id = audit.json()["id"]

    assert client.get(f"/api/audits/{audit_id}").status_code == 200
    assert client.get("/api/audits/9999").status_code == 404

    res = client.get(f"/api/results/{audit_id}")
    assert res.status_code == 200
    # Phase 10: engine evaluates the 1 DB rule (NET-001) against the config.
    # `hostname X` has no telnet info -> strict FAIL with honest evidence.
    results = res.json()
    assert len(results) == 1
    assert results[0]["rule_code"] == "NET-001"
    assert results[0]["status"] == "FAIL"
    assert results[0]["evidence"] != ""


def test_mappings_and_stubs():
    m = client.post(
        "/api/mappings",
        json={
            "vendor": "juniper",
            "raw_pattern": "set xyz secure-admin-mode enabled",
            "normalized_field": "management.secure_admin_mode",
            "suggested_category": "Management Security",
            "confidence": 0.82,
            "status": "confirmed",
            "confirmed_by": "admin",
        },
    )
    assert m.status_code == 201, m.text
    dup = client.post(
        "/api/mappings",
        json={"vendor": "juniper", "raw_pattern": "set xyz secure-admin-mode enabled"},
    )
    assert dup.status_code == 409
    assert client.get("/api/mappings").status_code == 200

    ai = client.post("/api/ai/analyze", json={"text": "set xyz ...", "vendor": "juniper"})
    # Phase 11: always 200 with honest ai_available flag (fallback when no key).
    assert ai.status_code == 200
    assert ai.json()["requires_confirmation"] is True
    assert "ai_available" in ai.json()

    rep = client.get("/api/reports/99999")
    # Phase 14: real PDF endpoint; nonexistent audit -> 404 (audit #1 exists
    # in the shared test DB, created by the audit test above).
    assert rep.status_code == 404
