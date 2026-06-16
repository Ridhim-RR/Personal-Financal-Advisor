from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.deps import get_current_user, get_transaction_service, get_analysis_service
from src.services.transaction_service import TransactionService
from src.services.analysis_service import AnalysisService

router = APIRouter()


class LogTradeRequest(BaseModel):
    ticker: str
    action: str       # buy | sell
    quantity: float
    price: float


@router.get("/")
async def list_transactions(
    ticker: str = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user),
    svc: TransactionService = Depends(get_transaction_service),
):
    records = svc.get_history(user_id, limit=limit, ticker=ticker)
    return {
        "transactions": [
            {
                "id": r.id,
                "ticker": r.ticker,
                "action": r.action,
                "quantity": r.quantity,
                "price": r.price,
                "total": r.total,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in records
        ]
    }


@router.post("/")
async def log_trade(
    body: LogTradeRequest,
    user_id: str = Depends(get_current_user),
    svc: TransactionService = Depends(get_transaction_service),
):
    trade = svc.log_trade(user_id, body.ticker, body.action, body.quantity, body.price)
    return {
        "id": trade.id,
        "ticker": trade.ticker,
        "action": trade.action,
        "quantity": trade.quantity,
        "price": trade.price,
        "total": trade.total,
    }


@router.get("/analysis")
async def list_analysis(
    ticker: str = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user),
    svc: AnalysisService = Depends(get_analysis_service),
):
    records = svc.get_history(user_id, limit=limit, ticker=ticker)
    return {
        "analyses": [
            {
                "id": r.id,
                "ticker": r.ticker,
                "agent_name": r.agent_name,
                "signal": r.signal,
                "confidence": r.confidence,
                "reasoning": r.reasoning,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in records
        ]
    }
