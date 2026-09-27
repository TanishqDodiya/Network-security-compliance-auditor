"""Phase 2 test: verify all 7 tables can be created and used.

Run from backend/ (venv activated):

    python -m pytest tests/test_database.py -v

Beginner note: this test uses a temporary in-memory database,
so it never touches your real auditor.db file.
"""

from app.database.session import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    AuditResult,
    AuditRun,
    ComplianceRule,
    Configuration,
    Device,
    UnknownMapping,
    User,
)


def test_all_tables_create_and_basic_crud():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # 1. All 7 expected tables exist.
    expected = {
        "users",
        "devices",
        "configurations",
        "audit_runs",
        "compliance_rules",
        "audit_results",
        "unknown_mappings",
    }
    assert expected.issubset(set(Base.metadata.tables.keys()))

    # 2. Device -> configuration -> audit_run -> audit_result chain works.
    device = Device(name="Test-Router-01", vendor="cisco")
    db.add(device)
    db.commit()

    config = Configuration(
        device_id=device.id,
        filename="test.conf",
        file_size=100,
        detected_vendor="cisco",
        raw_content="hostname Test-Router-01",
        status="ready",
    )
    db.add(config)
    db.commit()

    rule = ComplianceRule(
        rule_code="NET-001",
        title="Telnet must be disabled",
        category="Secure Management",
        severity="HIGH",
        framework=["Demo Security Rule"],
        field="management.telnet_enabled",
        expected=False,
        description="Telnet transmits credentials without adequate protection.",
        remediation="Disable Telnet and use SSH.",
    )
    db.add(rule)
    db.commit()

    run = AuditRun(device_id=device.id, configuration_id=config.id, status="completed")
    db.add(run)
    db.commit()

    result = AuditResult(
        audit_run_id=run.id,
        rule_id=rule.id,
        rule_code="NET-001",
        title=rule.title,
        status="FAIL",
        severity="HIGH",
        evidence="Telnet service is enabled",
        remediation="Disable Telnet and use SSH",
    )
    db.add(result)

    mapping = UnknownMapping(
        vendor="juniper",
        raw_pattern="set xyz secure-admin-mode enabled",
        normalized_field="management.secure_admin_mode",
        suggested_category="Management Security",
        confidence=0.82,
        status="confirmed",
        confirmed_by="admin",
    )
    db.add(mapping)

    user = User(username="admin", hashed_password="", role="admin")
    db.add(user)
    db.commit()

    assert db.query(Device).count() == 1
    assert db.query(AuditResult).filter_by(rule_code="NET-001").one().status == "FAIL"
    assert db.query(UnknownMapping).filter_by(status="confirmed").count() == 1
    db.close()
