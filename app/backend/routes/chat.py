from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.backend.routes.auth import get_current_user
from src.main import run_personalized_advisor

router = APIRouter(prefix="/chat", tags=["chat"])


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
):
    result = run_personalized_advisor(
        tickers=body.tickers,
        start_date=body.start_date or "",
        end_date=body.end_date or "",
        portfolio={},
        user_id=user_id,
        user_message=body.message,
        show_reasoning=body.show_reasoning,
    )
    return result
