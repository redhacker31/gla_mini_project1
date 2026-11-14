"""Database Schema Initialization and Migration Utility."""
from sqlalchemy.engine import Engine

from app.database.base import Base
from app.database.session import engine as default_engine
import app.models  # noqa: F401 - ensure models register with Base.metadata


def init_db(engine: Engine = default_engine) -> None:
    """Create all configured database tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


def drop_db(engine: Engine = default_engine) -> None:
    """Drop all configured database tables (used for test suite isolation)."""
    Base.metadata.drop_all(bind=engine)
