"""Phase 8 test: Palo Alto parser extracts security fields + evidence."""

from pathlib import Path

from app.parsers.paloalto import PaloAltoParser

SAMPLES = Path(__file__).resolve().parents[2] / "sample_configs" / "paloalto"
parser = PaloAltoParser()


def test_compliant_sample_parses_secure():
    text = (SAMPLES / "paloalto_compliant.conf").read_text(encoding="utf-8")
    r = parser.parse(text)
    assert r.hostname == "PaloAlto-FW-01"
    assert r.telnet_enabled is False
    assert r.ssh_enabled is True
    assert r.http_enabled is False
    assert r.https_enabled is True
    assert r.logging_enabled is True
    assert r.ntp_configured is True and len(r.ntp_servers) == 2
    assert r.snmp_insecure is False
    assert r.strong_auth is True
    assert r.weak_creds_found is False
    assert r.unnecessary_services is False
    assert r.mgmt_restricted is True
    assert "https" in r.evidence["https_enabled"].lower()


def test_noncompliant_sample_parses_insecure():
    text = (SAMPLES / "paloalto_noncompliant.conf").read_text(encoding="utf-8")
    r = parser.parse(text)
    assert r.hostname == "PaloAlto-FW-02"
    assert r.telnet_enabled is True
    assert r.ssh_enabled is False
    assert r.http_enabled is True
    assert r.https_enabled is False
    assert r.logging_enabled is False
    assert r.ntp_configured is False
    assert r.snmp_enabled is True
    assert r.snmp_insecure is True
    assert r.weak_creds_found is True
    assert r.strong_auth is False
    assert r.unnecessary_services is True
    assert r.mgmt_restricted is False
    assert "public" in r.evidence["snmp_insecure"].lower()


def test_empty_and_unknown_do_not_crash():
    r = parser.parse("")
    assert r.hostname is None
    assert r.telnet_enabled is None

    r = parser.parse("set deviceconfig system hostname FW1\nset xyz secure-admin-mode enabled\n")
    assert r.hostname == "FW1"
    assert any("secure-admin-mode" in u for u in r.unknown_lines)
