from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.routes.auth import get_current_user
from app.backend.database.connection import get_db
from src.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


class CreateWatchlistRequest(BaseModel):
    name: str
    tickers: list[str] = []


class UpdateWatchlistRequest(BaseModel):
    name: Optional[str] = None
    tickers: Optional[list[str]] = None


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("/")
def list_watchlists(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    watchlists = svc.get_watchlists(user_id)
    return {
        "watchlists": [
            {"id": w.id, "name": w.name, "tickers": w.tickers or []}
            for w in watchlists
        ]
    }


@router.post("/")
def create_watchlist(body: CreateWatchlistRequest, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    wl = svc.create_watchlist(user_id, body.name, body.tickers)
    return {"id": wl.id, "name": wl.name, "tickers": wl.tickers or []}


@router.put("/{watchlist_id}")
def update_watchlist(watchlist_id: str, body: UpdateWatchlistRequest, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    wl = svc.update_watchlist(watchlist_id, **updates)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return {"id": wl.id, "name": wl.name, "tickers": wl.tickers or []}


@router.delete("/{watchlist_id}")
def delete_watchlist(watchlist_id: str, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    svc.delete_watchlist(watchlist_id)
    return {"message": "Watchlist deleted"}


@router.post("/{watchlist_id}/tickers")
def add_ticker_to_watchlist(watchlist_id: str, body: AddTickerRequest, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    wl = svc.add_ticker_to_watchlist(watchlist_id, body.ticker)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return {"id": wl.id, "name": wl.name, "tickers": wl.tickers or []}


@router.delete("/{watchlist_id}/tickers/{ticker}")
def remove_ticker_from_watchlist(watchlist_id: str, ticker: str, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    wl = svc.remove_ticker_from_watchlist(watchlist_id, ticker)
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return {"id": wl.id, "name": wl.name, "tickers": wl.tickers or []}
