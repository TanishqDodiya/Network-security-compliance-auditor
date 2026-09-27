"""Phase 4 test: upload hardening + all 6 sample configs.

Run from backend/ (venv activated):
    python -m pytest tests/test_upload.py -v

Beginner note: samples live in ../../sample_configs/.
The API treats them as untrusted text and never executes them.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from db_helper import override_get_db, reset_test_schema

from app.database.session import get_db
from app.main import app

app.dependency_overrides[get_db] = override_get_db
reset_test_schema()
client = TestClient(app)

SAMPLES = Path(__file__).resolve().parents[2] / "sample_configs"


def _upload(filename: str, content: bytes, device_name: str | None = None):
    data = {}
    if device_name:
        data["device_name"] = device_name
    return client.post(
        "/api/configurations/upload",
        files={"file": (filename, content, "text/plain")},
        data=data,
    )


def test_all_sample_configs_upload_successfully():
    cases = [
        ("cisco/cisco_compliant.conf", "Cisco-Compliant-01", "cisco"),
        ("cisco/cisco_noncompliant.conf", "Cisco-NonCompliant-01", "cisco"),
        ("juniper/juniper_compliant.conf", "Juniper-Compliant-01", "juniper"),
        ("juniper/juniper_noncompliant.conf", "Juniper-NonCompliant-01", "juniper"),
        ("paloalto/paloalto_compliant.conf", "PaloAlto-Compliant-01", "paloalto"),
        ("paloalto/paloalto_noncompliant.conf", "PaloAlto-NonCompliant-01", "paloalto"),
    ]
    for rel, device, vendor in cases:
        content = (SAMPLES / rel).read_bytes()
        assert len(content) > 0, f"Sample empty: {rel}"
        r = _upload(Path(rel).name, content, device)
        assert r.status_code == 201, f"{rel}: {r.text}"
        body = r.json()
        assert body["file_size"] == len(content)
        assert body["line_count"] >= 5
        assert body["status"] == "Ready for Audit"
        assert body["detected_vendor"] == vendor, f"{rel}: got {body['detected_vendor']}"


def test_upload_rejections():
    # Wrong extension.
    assert _upload("evil.exe", b"data").status_code == 400
    # Empty file.
    assert _upload("empty.conf", b"").status_code == 400
    # Whitespace only.
    assert _upload("blank.conf", b"   \n  ").status_code == 400
    # Binary (null bytes).
    assert _upload("bin.conf", b"abc\x00def").status_code == 400
    # Path traversal in filename gets sanitized, still accepted as safe name.
    r = _upload("../../etc/passwd.conf", b"hostname X")
    assert r.status_code == 201
    assert ".." not in r.json()["filename"]
    assert "/" not in r.json()["filename"]
