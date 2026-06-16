"""Alert CRUD service backed by PostgreSQL."""

from typing import Optional, List

from sqlalchemy.orm import Session

from src.db.models import AlertORM
from src.db.repository import BaseRepository


class AlertService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = BaseRepository(AlertORM, session)

    def get_alerts(self, user_id: str, active_only: bool = False) -> List[AlertORM]:
        filters = {"user_id": user_id}
        if active_only:
            filters["active"] = True
        return self.repo.list(**filters)

    def create_alert(self, user_id: str, ticker: str, alert_type: str, threshold: float) -> AlertORM:
        return self.repo.create(
            user_id=user_id,
            ticker=ticker.upper(),
            alert_type=alert_type,
            threshold=threshold,
        )

    def update_alert(self, alert_id: str, **updates) -> Optional[AlertORM]:
        return self.repo.update(alert_id, **updates)

    def delete_alert(self, alert_id: str) -> bool:
        return self.repo.delete(alert_id)

    def get_alert(self, alert_id: str) -> Optional[AlertORM]:
        return self.repo.get(alert_id)
