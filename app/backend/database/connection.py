from typing import Generator
from sqlalchemy.orm import Session

from src.db.connection import DatabaseManager, Base

_db_manager: DatabaseManager = None


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.connect()
    return _db_manager


def get_db() -> Generator[Session, None, None]:
    manager = get_db_manager()
    session = manager._session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
