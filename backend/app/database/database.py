from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = DATABASE_DIR.parent.parent / "sahayak.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and run safe schema migrations."""
    from app.database import models  # ensure models are registered
    Base.metadata.create_all(bind=engine)

    # Safe migration for new columns on existing SQLite database
    import sqlite3
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(documents)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        new_columns = [
            ("expected_type", "VARCHAR(100)"),
            ("classification_status", "VARCHAR(50)"),
            ("verification_status", "VARCHAR(50)"),
            ("message", "TEXT"),
        ]
        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_type}")
        conn.commit()
        conn.close()
    except Exception as e:
        # If table doesn't exist yet or other non-critical error, continue
        pass
