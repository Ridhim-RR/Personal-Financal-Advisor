from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from src.api.deps import get_current_user, get_portfolio_service
from src.services.portfolio_service import PortfolioService

router = APIRouter()


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
async def get_portfolio(
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    holdings = svc.get_holdings(user_id)
    return {
        "holdings": [
            {
                "ticker": h.ticker,
                "shares": h.shares,
                "avg_cost": h.avg_cost,
                "target_allocation": h.target_allocation,
            }
            for h in holdings
        ]
    }


@router.post("/holdings")
async def add_holding(
    body: AddHoldingRequest,
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    holding = svc.add_holding(user_id, body.ticker, body.shares, body.avg_cost, body.target_allocation)
    return {"message": "Holding added", "ticker": holding.ticker}


@router.put("/holdings/{ticker}")
async def update_holding(
    ticker: str,
    body: UpdateHoldingRequest,
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    holding = svc.upsert_holding(user_id, ticker, **updates)
    return {"message": "Holding updated", "ticker": holding.ticker}


@router.delete("/holdings/{ticker}")
async def remove_holding(
    ticker: str,
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    svc.remove_holding(user_id, ticker)
    return {"message": "Holding removed"}


@router.get("/allocation")
async def get_target_allocation(
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    holdings = svc.get_holdings(user_id)
    return {
        "allocations": {
            h.ticker: h.target_allocation or 0
            for h in holdings
        }
    }


@router.put("/allocation")
async def update_target_allocation(
    body: SetAllocationRequest,
    user_id: str = Depends(get_current_user),
    svc: PortfolioService = Depends(get_portfolio_service),
):
    svc.upsert_holding(user_id, body.ticker, target_allocation=body.target_allocation)
    return {"message": "Target allocation updated"}
