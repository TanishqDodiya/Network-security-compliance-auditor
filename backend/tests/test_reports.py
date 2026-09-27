"""Phase 14 test: PDF report downloads and contains audit data."""

from pathlib import Path

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

SAMPLES = Path(__file__).resolve().parents[2] / "sample_configs"


def _audit_for(sample_rel: str) -> int:
    up = client.post(
        "/api/configurations/upload",
        files={"file": (Path(sample_rel).name, (SAMPLES / sample_rel).read_bytes(), "text/plain")},
    )
    assert up.status_code == 201, up.text
    audit = client.post("/api/audits", json={"configuration_id": up.json()["configuration_id"]})
    assert audit.status_code == 201, audit.text
    return audit.json()["id"]


def test_pdf_download_contains_report():
    audit_id = _audit_for("cisco/cisco_noncompliant.conf")
    r = client.get(f"/api/reports/{audit_id}")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 2000
    # Compression disabled -> device name and title searchable in bytes.
    assert b"cisco_noncompliant" in r.content
    assert b"NET-001" in r.content
    assert b"Failed Rules" in r.content
    assert 'filename="audit-' in r.headers["content-disposition"]


def test_pdf_404_and_compliant_variant():
    assert client.get("/api/reports/9999").status_code == 404
    audit_id = _audit_for("juniper/juniper_compliant.conf")
    r = client.get(f"/api/reports/{audit_id}")
    assert r.status_code == 200
    assert b"juniper_compliant" in r.content
