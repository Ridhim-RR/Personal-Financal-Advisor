from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from src.api.deps import get_current_user, get_recommendation_service
from src.main import run_personalized_advisor
from src.services.recommendation_service import RecommendationService
from src.utils.analysts import DEFAULT_PERSONALIZED_ANALYSTS

router = APIRouter()


class RecommendationRequest(BaseModel):
    tickers: list[str]
    start_date: str = ""
    end_date: str = ""
    user_message: str = ""
    show_reasoning: bool = False
    selected_analysts: list[str] = None


class FeedbackRequest(BaseModel):
    action: str  # "followed" | "ignored"


@router.post("/")
async def get_recommendation(
    body: RecommendationRequest,
    user_id: str = Depends(get_current_user),
):
    portfolio = {}
    portfolio_svc = None
    try:
        from src.api.deps import get_db
        session = next(get_db())
        svc_u = __import__("src.services.portfolio_service", fromlist=[""]).PortfolioService(session)
        portfolio = svc_u.get_holdings_dict(user_id)
    except Exception:
        portfolio = {}

    result = run_personalized_advisor(
        tickers=body.tickers,
        start_date=body.start_date or "",
        end_date=body.end_date or "",
        portfolio=portfolio,
        user_id=user_id,
        user_message=body.user_message or None,
        show_reasoning=body.show_reasoning,
        selected_analysts=body.selected_analysts if body.selected_analysts is not None else DEFAULT_PERSONALIZED_ANALYSTS,
    )
    return result


@router.get("/history")
async def get_recommendation_history(
    limit: int = 50,
    user_id: str = Depends(get_current_user),
    svc: RecommendationService = Depends(get_recommendation_service),
):
    records = svc.get_history(user_id, limit=limit)
    return {
        "recommendations": [
            {
                "id": r.id,
                "ticker": r.ticker,
                "signal": r.signal,
                "confidence": r.confidence,
                "reasoning": r.reasoning,
                "user_action": r.user_action,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in records
        ]
    }


@router.post("/{recommendation_id}/feedback")
async def record_feedback(
    recommendation_id: str,
    body: FeedbackRequest,
    user_id: str = Depends(get_current_user),
    svc: RecommendationService = Depends(get_recommendation_service),
):
    rec = svc.get_recommendation(recommendation_id)
    if not rec or rec.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    svc.record_feedback(recommendation_id, body.action)
    return {"message": f"Feedback recorded: {body.action}"}
