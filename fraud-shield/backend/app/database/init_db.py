"""Database Schema Initialization and Migration Utility."""
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.database.base import Base
from app.database.session import engine as default_engine
import app.models  # noqa: F401 - ensure models register with Base.metadata


def init_db(engine: Engine = default_engine) -> None:
    """Create all configured database tables and apply lightweight column migrations."""
    Base.metadata.create_all(bind=engine)

    # Lightweight migration for pre-existing SQLite DBs missing `device_hash`
    if str(engine.url).startswith("sqlite"):
        with engine.connect() as conn:
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(transactions)")).fetchall()}
            if cols and "device_hash" not in cols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN device_hash VARCHAR(64)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transactions_device_hash ON transactions (device_hash)"))
                conn.commit()


def drop_db(engine: Engine = default_engine) -> None:
    """Drop all configured database tables (used for test suite isolation)."""
    Base.metadata.drop_all(bind=engine)
