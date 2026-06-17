import os
from contextlib import contextmanager
from typing import Optional, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import NullPool

Base = declarative_base()


class DatabaseManager:
    """Manages the SQLAlchemy engine and session factory.

    Development: uses SQLite (no external DB needed).
    Production:  set DATABASE_URL to a PostgreSQL connection string.
    """

    def __init__(self, database_url: Optional[str] = None):
        raw_url = database_url or os.getenv("DATABASE_URL")
        if raw_url and "postgresql" in raw_url:
            self.database_url = raw_url
        elif raw_url and raw_url != "postgresql+psycopg2://user:pass@localhost:5432/ai_investment_advisor":
            self.database_url = raw_url
        else:
            # Default to SQLite for local development
            db_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".data")
            os.makedirs(db_dir, exist_ok=True)
            self.database_url = f"sqlite:///{os.path.join(db_dir, 'advisor.db')}"

        connect_args = {}
        if "sqlite" in self.database_url:
            connect_args["check_same_thread"] = False

        self._engine = create_engine(
            self.database_url,
            connect_args=connect_args,
            echo=False,
            # Allow multiple sessions in SQLite (dev)
            poolclass=None if "sqlite" in self.database_url else None,
        )
        self._session_factory = sessionmaker(bind=self._engine, autocommit=False, autoflush=False)

    def connect(self) -> None:
        """Create all tables defined in models that import Base."""
        from src.db.models import (  # noqa: F401 – registers models on Base
            UserORM, UserProfileORM, PortfolioORM, WatchlistORM,
            RecommendationLogORM, HoldingORM, AlertORM,
            TransactionORM, AgentAnalysisORM,
        )
        from app.backend.database.models import (  # noqa: F401 – registers hedge fund flow models
            HedgeFundFlow, HedgeFundFlowRun, HedgeFundFlowRunCycle, ApiKey,
        )
        Base.metadata.create_all(self._engine)

    def disconnect(self) -> None:
        self._engine.dispose()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Yield a session, committing on success, rolling back on error."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @property
    def is_connected(self) -> bool:
        return self._engine is not None
