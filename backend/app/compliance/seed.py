"""Shared rule seeding: insert/update the 10 demo rules, never duplicate.

Used by `seed_rules.py` (manual) and by app startup (auto-seed on empty DB
so fresh deploys work without an extra step).
"""

from app.compliance.rules_data import DEMO_RULES
from app.models.compliance_rule import ComplianceRule


def ensure_demo_rules(db) -> tuple[int, int]:
    """Returns (seeded_count, total_count). Idempotent and safe to re-run."""
    created = 0
    for data in DEMO_RULES:
        # pass_on_none is engine-only logic, not a DB column.
        clean = {k: v for k, v in data.items() if k != "pass_on_none"}
        existing = db.query(ComplianceRule).filter_by(rule_code=clean["rule_code"]).first()
        if existing:
            for key, value in clean.items():
                setattr(existing, key, value)
        else:
            db.add(ComplianceRule(**clean))
            created += 1
    db.commit()
    return created, db.query(ComplianceRule).count()
