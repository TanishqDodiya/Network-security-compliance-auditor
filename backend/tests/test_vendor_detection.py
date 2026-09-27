"""Phase 5 test: vendor detection (deterministic, no AI).

Run from backend/ (venv activated):
    python -m pytest tests/test_vendor_detection.py -v
"""

from pathlib import Path

from fastapi.testclient import TestClient

from db_helper import override_get_db, reset_test_schema

from app.database.session import get_db
from app.main import app
from app.services.vendor_detector import detect_vendor

app.dependency_overrides[get_db] = override_get_db
reset_test_schema()
client = TestClient(app)

SAMPLES = Path(__file__).resolve().parents[2] / "sample_configs"


def test_cisco_detection():
    text = "hostname R1\ninterface Gi0/0\naccess-list 10 permit any\nline vty 0 4\n"
    result = detect_vendor(text)
    assert result.vendor == "cisco"
    assert result.confidence > 0
    assert len(result.evidence) > 0


def test_juniper_detection():
    text = "set system host-name SW1\nset system services ssh\nset security zones test\n"
    result = detect_vendor(text)
    assert result.vendor == "juniper"


def test_paloalto_detection():
    text = "set deviceconfig system hostname FW1\nset rulebase security rules Allow action allow\n"
    result = detect_vendor(text)
    assert result.vendor == "paloalto"


def test_unknown_on_weak_signal():
    assert detect_vendor("hostname lonely").vendor == "unknown"
    assert detect_vendor("hello world, this is not a config").vendor == "unknown"
    assert detect_vendor("").vendor == "unknown"


def test_all_sample_files_detected():
    expected = {
        "cisco/cisco_compliant.conf": "cisco",
        "cisco/cisco_noncompliant.conf": "cisco",
        "juniper/juniper_compliant.conf": "juniper",
        "juniper/juniper_noncompliant.conf": "juniper",
        "paloalto/paloalto_compliant.conf": "paloalto",
        "paloalto/paloalto_noncompliant.conf": "paloalto",
    }
    for rel, vendor in expected.items():
        text = (SAMPLES / rel).read_text(encoding="utf-8")
        assert detect_vendor(text).vendor == vendor, f"Failed: {rel}"


def test_detect_endpoint_and_upload_uses_it():
    r = client.post("/api/detect", json={"text": "hostname R1\ninterface Gi0/0\nline vty 0 4\n"})
    assert r.status_code == 200
    assert r.json()["vendor"] == "cisco"

    up = client.post(
        "/api/configurations/upload",
        files={"file": ("detect-cisco.conf", b"hostname R1\ninterface Gi0/0\nline vty 0 4\n", "text/plain")},
    )
    assert up.status_code == 201
    assert up.json()["detected_vendor"] == "cisco"
