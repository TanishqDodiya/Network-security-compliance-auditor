"""Phase 6 test: Cisco parser extracts security fields + evidence.

Run from backend/ (venv activated):
    python -m pytest tests/test_cisco_parser.py -v
"""

from pathlib import Path

from app.parsers.cisco import CiscoParser

SAMPLES = Path(__file__).resolve().parents[2] / "sample_configs" / "cisco"
parser = CiscoParser()


def test_compliant_sample_parses_secure():
    text = (SAMPLES / "cisco_compliant.conf").read_text(encoding="utf-8")
    r = parser.parse(text)
    assert r.hostname == "Cisco-Router-01"
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
    # Evidence must point at real config lines.
    assert "telnet" in r.evidence["telnet_enabled"].lower()
    assert r.evidence["ntp_configured"].lower().startswith("ntp server")


def test_noncompliant_sample_parses_insecure():
    text = (SAMPLES / "cisco_noncompliant.conf").read_text(encoding="utf-8")
    r = parser.parse(text)
    assert r.hostname == "Cisco-Router-02"
    assert r.telnet_enabled is True
    assert r.http_enabled is True
    assert r.https_enabled in (False, None)
    assert r.logging_enabled in (False, None)
    assert r.ntp_configured in (False, None)
    assert r.snmp_enabled is True
    assert r.snmp_insecure is True
    assert r.weak_creds_found is True
    assert r.strong_auth is False
    assert r.unnecessary_services is True  # finger/pad/source-route on
    assert r.mgmt_restricted is False
    assert "public" in r.evidence["snmp_insecure"].lower()


def test_vty_transport_inference():
    r = parser.parse("hostname R1\nline vty 0 4\n transport input ssh\n")
    assert r.telnet_enabled is False
    assert r.ssh_enabled is True

    r = parser.parse("hostname R1\nline vty 0 4\n transport input all\n")
    assert r.telnet_enabled is True


def test_empty_and_unknown_lines_do_not_crash():
    r = parser.parse("")
    assert r.hostname is None
    assert r.telnet_enabled is None

    r = parser.parse("hostname R1\nsupercalifragilistic feature turbo on\n")
    assert r.hostname == "R1"
    assert any("supercalifragilistic" in u for u in r.unknown_lines)
