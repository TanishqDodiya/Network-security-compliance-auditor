"""Create the SQLite database file and all tables.

Run from the backend/ folder (venv activated):

    python init_db.py

Safe to run many times: it creates missing tables but never deletes data.
"""

from app.database.session import DATABASE_URL, engine, init_db


def main() -> None:
    print(f"Using database: {DATABASE_URL}")
    init_db()
    # List created tables so beginners can see the result.
    from app.database.session import Base

    print("Tables created:")
    for table in sorted(Base.metadata.tables):
        print(f"  - {table}")
    print(f"SQLite file ready (engine: {engine.url}).")


if __name__ == "__main__":
    main()
