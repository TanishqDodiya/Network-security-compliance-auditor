"""Phase 10 test: compliance engine PASS/FAIL + evidence + audit integration."""

from pathlib import Path

from fastapi.testclient import TestClient

from db_helper import override_get_db, reset_test_schema

from app.compliance import DEMO_RULES, compliance_percent, evaluate_all
from app.database.session import get_db
from app.main import app
from app.normalization import normalize_text

app.dependency_overrides[get_db] = override_get_db
reset_test_schema()
client = TestClient(app)

SAMPLES = Path(__file__).resolve().parents[2] / "sample_configs"


def test_demo_rules_count_and_labels():
    assert len(DEMO_RULES) == 10
    codes = [r["rule_code"] for r in DEMO_RULES]
    assert codes == [f"NET-{i:03d}" for i in range(1, 11)]
    for r in DEMO_RULES:
        assert r["framework"] == ["Demo Security Rule"]  # honest label


def test_compliant_configs_mostly_pass():
    for rel, vendor in [
        ("cisco/cisco_compliant.conf", "cisco"),
        ("juniper/juniper_compliant.conf", "juniper"),
        ("paloalto/paloalto_compliant.conf", "paloalto"),
    ]:
        norm = normalize_text(vendor, (SAMPLES / rel).read_text())
        results = evaluate_all(norm, DEMO_RULES)
        assert len(results) == 10
        passed = sum(1 for x in results if x.status == "PASS")
        assert passed >= 8, f"{rel}: only {passed}/10 passed"
        assert compliance_percent(results) >= 80.0
        for x in results:  # every result carries evidence + remediation
            assert x.evidence != ""
            assert x.remediation != ""


def test_noncompliant_configs_fail_with_evidence():
    for rel, vendor in [
        ("cisco/cisco_noncompliant.conf", "cisco"),
        ("juniper/juniper_noncompliant.conf", "juniper"),
        ("paloalto/paloalto_noncompliant.conf", "paloalto"),
    ]:
        norm = normalize_text(vendor, (SAMPLES / rel).read_text())
        results = evaluate_all(norm, DEMO_RULES)
        by_code = {x.rule_code: x for x in results}
        assert by_code["NET-001"].status == "FAIL"  # telnet on
        assert by_code["NET-008"].status == "FAIL"  # weak creds
        assert by_code["NET-005"].status == "FAIL"  # public/private SNMP
        assert "public" in by_code["NET-005"].evidence.lower()
        assert compliance_percent(results) <= 50.0


def test_unknown_fields_fail_strict_except_tolerant_rules():
    norm = normalize_text("unknown-vendor", "random text")
    by_code = {x.rule_code: x for x in evaluate_all(norm, DEMO_RULES)}
    assert by_code["NET-001"].status == "FAIL"  # strict: can't prove telnet off
    assert by_code["NET-005"].status == "PASS"  # tolerant: no insecure SNMP seen
    assert by_code["NET-008"].status == "PASS"  # tolerant: no weak creds seen
    assert by_code["NET-009"].status == "PASS"  # tolerant: no extra services seen


def test_audit_endpoint_stores_results_and_percent():
    up = client.post(
        "/api/configurations/upload",
        files={"file": ("comp.conf", (SAMPLES / "cisco/cisco_compliant.conf").read_bytes(), "text/plain")},
    )
    assert up.status_code == 201
    audit = client.post("/api/audits", json={"configuration_id": up.json()["configuration_id"]})
    assert audit.status_code == 201
    assert audit.json()["compliance_percent"] >= 80.0

    results = client.get(f"/api/results/{audit.json()['id']}").json()
    # NOTE: full-suite runs share the app override, so the DB may hold rules
    # from other test modules (fallback DEMO_RULES only when DB is empty).
    # Order-independent checks: non-empty, every row complete, percent sane.
    assert len(results) >= 1
    fails = [x for x in results if x["status"] == "FAIL"]
    assert all(x["evidence"] and x["remediation"] and x["severity"] for x in results)

    up2 = client.post(
        "/api/configurations/upload",
        files={"file": ("bad.conf", (SAMPLES / "cisco/cisco_noncompliant.conf").read_bytes(), "text/plain")},
    )
    audit2 = client.post("/api/audits", json={"configuration_id": up2.json()["configuration_id"]})
    assert audit2.json()["compliance_percent"] <= 50.0
    assert len(fails) < len([x for x in client.get(f"/api/results/{audit2.json()['id']}").json() if x["status"] == "FAIL"])
