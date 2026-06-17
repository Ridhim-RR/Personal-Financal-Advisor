from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.routes.auth import get_current_user
from app.backend.database.connection import get_db
from src.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class AddHoldingRequest(BaseModel):
    ticker: str
    shares: float = 0
    avg_cost: float = 0
    target_allocation: float = 0


class UpdateHoldingRequest(BaseModel):
    shares: Optional[float] = None
    avg_cost: Optional[float] = None
    target_allocation: Optional[float] = None


class SetAllocationRequest(BaseModel):
    ticker: str
    target_allocation: float


@router.get("/")
def get_portfolio(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    holdings = svc.get_holdings(user_id)
    return {
        "holdings": [
            {"ticker": h.ticker, "shares": h.shares, "avg_cost": h.avg_cost, "target_allocation": h.target_allocation}
            for h in holdings
        ]
    }


@router.post("/holdings")
def add_holding(body: AddHoldingRequest, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    holding = svc.add_holding(user_id, body.ticker, body.shares, body.avg_cost, body.target_allocation)
    return {"message": "Holding added", "ticker": holding.ticker}


@router.put("/holdings/{ticker}")
def update_holding(ticker: str, body: UpdateHoldingRequest, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    holding = svc.upsert_holding(user_id, ticker, **updates)
    return {"message": "Holding updated", "ticker": holding.ticker}


@router.delete("/holdings/{ticker}")
def remove_holding(ticker: str, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    svc.remove_holding(user_id, ticker)
    return {"message": "Holding removed"}


@router.get("/allocation")
def get_target_allocation(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    holdings = svc.get_holdings(user_id)
    return {"allocations": {h.ticker: h.target_allocation or 0 for h in holdings}}


@router.put("/allocation")
def update_target_allocation(body: SetAllocationRequest, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = PortfolioService(db)
    svc.upsert_holding(user_id, body.ticker, target_allocation=body.target_allocation)
    return {"message": "Target allocation updated"}
