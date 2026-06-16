"""Agent analysis history service backed by PostgreSQL."""

from typing import Optional, List

from sqlalchemy.orm import Session

from src.db.models import AgentAnalysisORM
from src.db.repository import BaseRepository


class AnalysisService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = BaseRepository(AgentAnalysisORM, session)

    def log_analysis(
        self,
        user_id: str,
        ticker: str,
        agent_name: str,
        signal: str,
        confidence: float = 0.0,
        reasoning: str = "",
        details: dict = None,
        recommendation_id: str = None,
    ) -> AgentAnalysisORM:
        return self.repo.create(
            user_id=user_id,
            ticker=ticker.upper(),
            agent_name=agent_name,
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            details=details or {},
            recommendation_id=recommendation_id,
        )

    def get_history(self, user_id: str, limit: int = 50, ticker: str = None) -> List[AgentAnalysisORM]:
        filters = {"user_id": user_id}
        if ticker:
            filters["ticker"] = ticker.upper()
        records = self.repo.list(**filters)
        records.sort(key=lambda r: r.created_at or "", reverse=True)
        return records[:limit]

    def get_by_recommendation(self, recommendation_id: str) -> List[AgentAnalysisORM]:
        return self.repo.list(recommendation_id=recommendation_id)
