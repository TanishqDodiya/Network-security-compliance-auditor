"""Create all tables in the PostgreSQL database.

Run from the backend/ folder (venv activated, DATABASE_URL set):

    python init_db.py

Safe to run many times: it creates missing tables but never deletes data.
"""

from app.database.session import DATABASE_URL, engine, init_db


def _redacted(url: str) -> str:
    """Hide the password when printing the database URL."""
    try:
        from sqlalchemy.engine import make_url

        parsed = make_url(url)
        if parsed.password:
            parsed = parsed.set(password="***")
        return str(parsed)
    except Exception:
        return "(unparseable DATABASE_URL)"


def main() -> None:
    print(f"Using database: {_redacted(DATABASE_URL)}")
    init_db()
    # List created tables so beginners can see the result.
    from app.database.session import Base

    print("Tables created:")
    for table in sorted(Base.metadata.tables):
        print(f"  - {table}")
    print(f"PostgreSQL ready (engine: {_redacted(str(engine.url))}).")


if __name__ == "__main__":
    main()
