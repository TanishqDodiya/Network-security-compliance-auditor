"""Seed the 10 demo compliance rules into the database.

Run from backend/ (venv activated):
    python seed_rules.py

Idempotent: re-running updates existing rules instead of duplicating them.
"""

from app.compliance.seed import ensure_demo_rules
from app.database.session import SessionLocal, init_db


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        created, total = ensure_demo_rules(db)
        print(f"Seeded {created} new demo rules. Total in DB: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
