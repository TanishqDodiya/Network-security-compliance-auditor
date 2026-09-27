"""Phase 15: gap tests (audits list, upload limits, rules-data validity).

Run from backend/ (venv activated):
    python -m pytest tests/test_gaps.py -v
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.compliance import DEMO_RULES
from app.database.session import Base, get_db
from app.main import app
from app.models.compliance_rule import ComplianceRule
from app.normalization import NormalizedConfig

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


def _upload(name: str, content: bytes):
    return client.post(
        "/api/configurations/upload",
        files={"file": (name, content, "text/plain")},
    )


def test_audits_list_endpoint():
    # Shared test DB: only assert our own runs appear, newest first.
    ids = []
    for i in range(2):
        up = _upload(f"gap-{i}.conf", b"hostname Gap\nip ssh version 2\n")
        assert up.status_code == 201
        run = client.post("/api/audits", json={"configuration_id": up.json()["configuration_id"]})
        assert run.status_code == 201
        ids.append(run.json()["id"])
    listed = client.get("/api/audits?limit=50").json()
    listed_ids = [a["id"] for a in listed]
    assert ids[0] in listed_ids and ids[1] in listed_ids
    assert listed_ids == sorted(listed_ids, reverse=True)
    assert len(client.get("/api/audits?limit=1").json()) == 1


def test_upload_size_and_line_limits():
    big = _upload("big.conf", b"x\n" * 10 + b"y" * (2 * 1024 * 1024))
    assert big.status_code == 413
    many_lines = _upload("many.conf", b"hostname X\n" + b"set interfaces ge-0/0/0 unit 0\n" * 20001)
    assert many_lines.status_code == 400
    assert "lines" in many_lines.json()["detail"].lower()


def test_demo_rules_valid_and_seeding_safe():
    codes = [r["rule_code"] for r in DEMO_RULES]
    assert len(set(codes)) == 10 == len(codes)
    valid_sev = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    columns = set(inspect(ComplianceRule).columns.keys())
    probe = NormalizedConfig()
    for r in DEMO_RULES:
        assert r["severity"] in valid_sev, r["rule_code"]
        assert r["framework"] == ["Demo Security Rule"]
        root = r["field"].split(".")[0]
        assert root in {"device", "management", "logging", "authentication", "snmp", "ntp"}, r["field"]
        assert probe.get_field(r["field"]) is None or True  # resolves without error
        # Regression: every key must fit the DB model (pass_on_none is engine-only).
        for key in r:
            assert key in columns or key == "pass_on_none", f"{r['rule_code']}.{key}"
