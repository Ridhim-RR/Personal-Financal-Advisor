from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.deps import get_current_user, get_portfolio_service, get_db
from src.main import run_personalized_advisor
from sqlalchemy.orm import Session

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    tickers: list[str] = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]
    start_date: str = ""
    end_date: str = ""
    show_reasoning: bool = False


@router.post("/")
async def chat(
    body: ChatRequest,
    user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    svc = __import__("src.services.portfolio_service", fromlist=[""]).PortfolioService(session)
    portfolio = svc.get_holdings_dict(user_id)

    end_date = body.end_date or datetime.now().strftime("%Y-%m-%d")
    start_date = body.start_date or (datetime.now() - relativedelta(months=3)).strftime("%Y-%m-%d")

    result = run_personalized_advisor(
        tickers=body.tickers,
        start_date=start_date,
        end_date=end_date,
        portfolio=portfolio,
        user_id=user_id,
        user_message=body.message,
        show_reasoning=body.show_reasoning,
    )
    return result
