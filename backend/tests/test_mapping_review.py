"""Phase 12 test: stored mappings reused before AI; confirm/reject flow."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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

PATTERN = "set xyz quantum-guard-mode enabled"


def test_resolve_new_pattern_calls_ai_suggestion():
    r = client.post("/api/mappings/resolve", json={"vendor": "juniper", "raw_pattern": PATTERN})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "ai"
    assert body["requires_confirmation"] is True


def test_full_human_loop_and_reuse():
    # 1. Create pending mapping (as if AI suggested, awaiting human).
    created = client.post("/api/mappings", json={
        "vendor": "juniper", "raw_pattern": PATTERN,
        "normalized_field": "", "suggested_category": "Management Security",
        "confidence": 0.7, "status": "pending", "confirmed_by": "",
    })
    assert created.status_code == 201
    mid = created.json()["id"]

    # 2. Pending shows in review queue, not as confirmed.
    pending = client.get("/api/mappings?status=pending").json()
    assert any(m["id"] == mid for m in pending)
    resolve_pending = client.post("/api/mappings/resolve", json={"vendor": "juniper", "raw_pattern": PATTERN}).json()
    assert resolve_pending["source"] == "stored"
    assert resolve_pending["requires_confirmation"] is True

    # 3. Human confirms with chosen field (confirm without field -> 400).
    assert client.patch(f"/api/mappings/{mid}", json={"status": "confirmed"}).status_code == 400
    ok = client.patch(f"/api/mappings/{mid}", json={
        "status": "confirmed",
        "normalized_field": "management.secure_admin_mode",
        "confirmed_by": "admin",
    })
    assert ok.status_code == 200
    assert ok.json()["status"] == "confirmed"

    # 4. Same pattern now reuses stored mapping, no AI, no confirmation needed.
    reused = client.post("/api/mappings/resolve", json={"vendor": "juniper", "raw_pattern": PATTERN}).json()
    assert reused["source"] == "stored"
    assert reused["suggested_field"] == "management.secure_admin_mode"
    assert reused["requires_confirmation"] is False

    # 5. Reject flow + 404 + bad filter.
    assert client.patch("/api/mappings/9999", json={"status": "confirmed", "normalized_field": "x"}).status_code == 404
    assert client.get("/api/mappings?status=bogus").status_code == 400
