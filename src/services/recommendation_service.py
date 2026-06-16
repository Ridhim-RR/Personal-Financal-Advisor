from typing import Optional, List

from sqlalchemy.orm import Session

from src.db.models import RecommendationLogORM
from src.db.repository import BaseRepository


class RecommendationService:
    """Logs and retrieves recommendation history in PostgreSQL.

    System of record for:
      - Every recommendation made (signal, confidence, reasoning)
      - What each agent contributed (agent_signals)
      - User follow-up action (followed / ignored)
    """

    def __init__(self, session: Session):
        self.session = session
        self.repo = BaseRepository(RecommendationLogORM, session)

    def log_recommendation(
        self,
        user_id: str,
        ticker: str,
        signal: str,
        confidence: float,
        reasoning: str,
        agent_signals: dict = None,
    ) -> RecommendationLogORM:
        return self.repo.create(
            user_id=user_id,
            ticker=ticker.upper(),
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            agent_signals=agent_signals or {},
        )

    def get_history(self, user_id: str, limit: int = 50) -> List[RecommendationLogORM]:
        records = self.repo.list(user_id=user_id)
        records.sort(key=lambda r: r.created_at or "", reverse=True)
        return records[:limit]

    def record_feedback(self, recommendation_id: str, action: str) -> Optional[RecommendationLogORM]:
        """User reports whether they followed or ignored."""
        return self.repo.update(recommendation_id, user_action=action)

    def get_recommendation(self, recommendation_id: str) -> Optional[RecommendationLogORM]:
        return self.repo.get(recommendation_id)
