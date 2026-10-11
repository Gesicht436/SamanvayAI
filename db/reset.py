"""Database reset script. Drops existing schema and applies fresh migrations."""

from sqlalchemy import text

from api.database import get_sync_engine


def reset_database():
    """Drop all tables and schema elements, then re-apply."""
    engine = get_sync_engine()
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()
    print("Database schema successfully reset.")


if __name__ == "__main__":
    reset_database()
