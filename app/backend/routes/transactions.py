from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.backend.routes.auth import get_current_user
from app.backend.database.connection import get_db
from src.services.transaction_service import TransactionService
from src.services.analysis_service import AnalysisService

router = APIRouter(prefix="/transactions", tags=["transactions"])


class LogTradeRequest(BaseModel):
    ticker: str
    action: str
    quantity: float
    price: float


@router.get("/")
def list_transactions(ticker: str = None, limit: int = 50, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = TransactionService(db)
    records = svc.get_history(user_id, limit=limit, ticker=ticker)
    return {
        "transactions": [
            {"id": r.id, "ticker": r.ticker, "action": r.action, "quantity": r.quantity, "price": r.price, "total": r.total, "created_at": str(r.created_at) if r.created_at else None}
            for r in records
        ]
    }


@router.post("/")
def log_trade(body: LogTradeRequest, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = TransactionService(db)
    trade = svc.log_trade(user_id, body.ticker, body.action, body.quantity, body.price)
    return {"id": trade.id, "ticker": trade.ticker, "action": trade.action, "quantity": trade.quantity, "price": trade.price, "total": trade.total}


@router.get("/analysis")
def list_analysis(ticker: str = None, limit: int = 50, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = AnalysisService(db)
    records = svc.get_history(user_id, limit=limit, ticker=ticker)
    return {
        "analyses": [
            {"id": r.id, "ticker": r.ticker, "agent_name": r.agent_name, "signal": r.signal, "confidence": r.confidence, "reasoning": r.reasoning, "created_at": str(r.created_at) if r.created_at else None}
            for r in records
        ]
    }
