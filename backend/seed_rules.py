"""Seed the 10 demo compliance rules into the database.

Run from backend/ (venv activated):
    python seed_rules.py

Idempotent: re-running updates existing rules instead of duplicating them.
"""

from app.compliance.rules_data import DEMO_RULES
from app.database.session import SessionLocal, init_db
from app.models.compliance_rule import ComplianceRule


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        for data in DEMO_RULES:
            # pass_on_none is engine-only logic, not a DB column.
            clean = {k: v for k, v in data.items() if k != "pass_on_none"}
            existing = db.query(ComplianceRule).filter_by(rule_code=clean["rule_code"]).first()
            if existing:
                for key, value in clean.items():
                    setattr(existing, key, value)
            else:
                db.add(ComplianceRule(**clean))
        db.commit()
        count = db.query(ComplianceRule).count()
        print(f"Seeded {len(DEMO_RULES)} demo rules. Total in DB: {count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
