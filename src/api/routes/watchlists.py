from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from src.api.deps import get_current_user, get_portfolio_service
from src.services.portfolio_service import PortfolioService

router = APIRouter()


class CreateWatchlistRequest(BaseModel):
    name: str
    tickers: list[str] = []


class UpdateWatchlistRequest(BaseModel):
    name: Optional[str] = None
    tickers: Optional[list[str]] = None


class AddTickerRequest(BaseModel):
    ticker: str


@router.get("/")
async def list_watchlists(
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    watchlists = svc.get_watchlists(user_id)
    return {
        "watchlists": [
            {"id": w.id, "name": w.name, "tickers": w.tickers or []}
            for w in watchlists
        ]
    }


@router.post("/")
async def create_watchlist(
    body: CreateWatchlistRequest,
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    wl = svc.create_watchlist(user_id, body.name, body.tickers)
    return {"id": wl.id, "name": wl.name, "tickers": wl.tickers or []}


@router.put("/{watchlist_id}")
async def update_watchlist(
    watchlist_id: str,
    body: UpdateWatchlistRequest,
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    wl = svc.update_watchlist(watchlist_id, **updates)
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return {"id": wl.id, "name": wl.name, "tickers": wl.tickers or []}


@router.delete("/{watchlist_id}")
async def delete_watchlist(
    watchlist_id: str,
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    svc.delete_watchlist(watchlist_id)
    return {"message": "Watchlist deleted"}


@router.post("/{watchlist_id}/tickers")
async def add_ticker_to_watchlist(
    watchlist_id: str,
    body: AddTickerRequest,
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    wl = svc.add_ticker_to_watchlist(watchlist_id, body.ticker)
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return {"id": wl.id, "name": wl.name, "tickers": wl.tickers or []}


@router.delete("/{watchlist_id}/tickers/{ticker}")
async def remove_ticker_from_watchlist(
    watchlist_id: str,
    ticker: str,
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    wl = svc.remove_ticker_from_watchlist(watchlist_id, ticker)
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return {"id": wl.id, "name": wl.name, "tickers": wl.tickers or []}
