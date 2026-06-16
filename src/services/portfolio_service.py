from typing import Optional, List

from sqlalchemy.orm import Session

from src.db.models import PortfolioORM, WatchlistORM
from src.db.repository import BaseRepository


class PortfolioService:
    """Manages portfolio holdings and watchlists in PostgreSQL.

    System of record for:
      - Holdings (ticker, shares, avg_cost)
      - Target allocation percentages
      - Named watchlists
    """

    def __init__(self, session: Session):
        self.session = session
        self.holding_repo = BaseRepository(PortfolioORM, session)
        self.watchlist_repo = BaseRepository(WatchlistORM, session)

    # ── Holdings ──────────────────────────────────────────────

    def get_holdings(self, user_id: str) -> List[PortfolioORM]:
        return self.holding_repo.list(user_id=user_id)

    def get_holdings_dict(self, user_id: str) -> dict:
        """Return {ticker: {shares, avg_cost, target_allocation}} for state."""
        holdings = self.get_holdings(user_id)
        return {
            h.ticker: {
                "shares": h.shares or 0,
                "avg_cost": h.avg_cost or 0,
                "target_allocation": h.target_allocation or 0,
            }
            for h in holdings
        }

    def add_holding(self, user_id: str, ticker: str, shares: float = 0, avg_cost: float = 0, target_allocation: float = 0) -> PortfolioORM:
        return self.holding_repo.create(
            user_id=user_id,
            ticker=ticker.upper(),
            shares=shares,
            avg_cost=avg_cost,
            target_allocation=target_allocation,
        )

    def upsert_holding(self, user_id: str, ticker: str, **updates) -> PortfolioORM:
        """Update an existing holding or create a new one."""
        existing = self.holding_repo.get_by(user_id=user_id, ticker=ticker.upper())
        if existing:
            return self.holding_repo.update(existing.id, **updates)
        return self.add_holding(user_id, ticker.upper(), **updates)

    def remove_holding(self, user_id: str, ticker: str) -> bool:
        existing = self.holding_repo.get_by(user_id=user_id, ticker=ticker.upper())
        if existing:
            return self.holding_repo.delete(existing.id)
        return False

    # ── Watchlists ────────────────────────────────────────────

    def get_watchlists(self, user_id: str) -> List[WatchlistORM]:
        return self.watchlist_repo.list(user_id=user_id)

    def create_watchlist(self, user_id: str, name: str, tickers: list = None) -> WatchlistORM:
        return self.watchlist_repo.create(
            user_id=user_id,
            name=name,
            tickers=tickers or [],
        )

    def update_watchlist(self, watchlist_id: str, **updates) -> Optional[WatchlistORM]:
        return self.watchlist_repo.update(watchlist_id, **updates)

    def delete_watchlist(self, watchlist_id: str) -> bool:
        return self.watchlist_repo.delete(watchlist_id)

    def get_watchlist(self, watchlist_id: str) -> Optional[WatchlistORM]:
        return self.watchlist_repo.get(watchlist_id)

    def add_ticker_to_watchlist(self, watchlist_id: str, ticker: str) -> Optional[WatchlistORM]:
        wl = self.get_watchlist(watchlist_id)
        if not wl:
            return None
        tickers = list(wl.tickers or [])
        ticker = ticker.upper()
        if ticker not in tickers:
            tickers.append(ticker)
        return self.watchlist_repo.update(watchlist_id, tickers=tickers)

    def remove_ticker_from_watchlist(self, watchlist_id: str, ticker: str) -> Optional[WatchlistORM]:
        wl = self.get_watchlist(watchlist_id)
        if not wl:
            return None
        tickers = list(wl.tickers or [])
        ticker = ticker.upper()
        if ticker in tickers:
            tickers.remove(ticker)
        return self.watchlist_repo.update(watchlist_id, tickers=tickers)
