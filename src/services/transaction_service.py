"""Transaction CRUD service backed by PostgreSQL."""

from typing import Optional, List

from sqlalchemy.orm import Session

from src.db.models import TransactionORM
from src.db.repository import BaseRepository


class TransactionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = BaseRepository(TransactionORM, session)

    def log_trade(self, user_id: str, ticker: str, action: str, quantity: float, price: float) -> TransactionORM:
        total = round(quantity * price, 2)
        return self.repo.create(
            user_id=user_id,
            ticker=ticker.upper(),
            action=action,
            quantity=quantity,
            price=price,
            total=total,
        )

    def get_history(self, user_id: str, limit: int = 50, ticker: str = None) -> List[TransactionORM]:
        filters = {"user_id": user_id}
        if ticker:
            filters["ticker"] = ticker.upper()
        records = self.repo.list(**filters)
        records.sort(key=lambda r: r.created_at or "", reverse=True)
        return records[:limit]
