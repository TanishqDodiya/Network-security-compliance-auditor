"""Phase 9 test: normalization produces one common model for all vendors."""

from pathlib import Path

from fastapi.testclient import TestClient

from db_helper import override_get_db, reset_test_schema

from app.database.session import get_db
from app.main import app
from app.normalization import normalize_text

app.dependency_overrides[get_db] = override_get_db
reset_test_schema()
client = TestClient(app)

SAMPLES = Path(__file__).resolve().parents[2] / "sample_configs"


def test_cisco_samples_normalize():
    good = normalize_text("cisco", (SAMPLES / "cisco/cisco_compliant.conf").read_text())
    assert good.device.vendor == "cisco"
    assert good.management.telnet_enabled is False
    assert good.ntp.configured is True
    assert good.evidence["management.telnet_enabled"].lower().startswith("no service telnet")
    assert good.get_field("management.telnet_enabled") is False

    bad = normalize_text("cisco", (SAMPLES / "cisco/cisco_noncompliant.conf").read_text())
    assert bad.management.telnet_enabled is True
    assert bad.snmp.insecure is True
    assert bad.authentication.weak_creds_found is True


def test_juniper_and_paloalto_normalize_to_same_shape():
    jun = normalize_text("juniper", (SAMPLES / "juniper/juniper_compliant.conf").read_text())
    pan = normalize_text("paloalto", (SAMPLES / "paloalto/paloalto_compliant.conf").read_text())
    for cfg in (jun, pan):
        assert cfg.management.ssh_enabled is True
        assert cfg.logging.enabled is True
        assert cfg.ntp.configured is True
        # Same dotted paths work for every vendor (compliance engine relies on this).
        assert cfg.get_field("logging.enabled") is True

    jun_bad = normalize_text("juniper", (SAMPLES / "juniper/juniper_noncompliant.conf").read_text())
    pan_bad = normalize_text("paloalto", (SAMPLES / "paloalto/paloalto_noncompliant.conf").read_text())
    assert jun_bad.management.telnet_enabled is True
    assert pan_bad.management.telnet_enabled is True


def test_unknown_vendor_and_endpoint():
    r = normalize_text("unknown-vendor", "some random text\nmore lines")
    assert r.device.vendor == "unknown"
    assert len(r.unknown_lines) > 0

    api = client.post("/api/normalize", json={"vendor": "cisco", "text": "hostname R1\nno service telnet\n"})
    assert api.status_code == 200
    assert api.json()["management"]["telnet_enabled"] is False
