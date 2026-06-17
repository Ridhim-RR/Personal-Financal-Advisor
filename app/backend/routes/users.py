from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.routes.auth import get_current_user
from app.backend.database.connection import get_db
from src.services.user_profile_service import UserProfileService
from src.services.conversation_memory_service import ConversationMemoryService

router = APIRouter(prefix="/users", tags=["users"])


class UpdateProfileRequest(BaseModel):
    risk_appetite: Optional[str] = None
    investment_goal: Optional[str] = None
    investment_horizon: Optional[str] = None
    preferred_sectors: Optional[list] = None
    excluded_sectors: Optional[list] = None
    preferred_analysts: Optional[list] = None
    initial_capital: Optional[float] = None


@router.get("/me")
def get_profile(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = UserProfileService(db)
    user = svc.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    profile = svc.get_profile_dict(user_id)
    return {"user_id": user.id, "email": user.email, "profile": profile}


@router.put("/me")
def update_profile(
    body: UpdateProfileRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = UserProfileService(db)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    profile = svc.update_profile(user_id, **updates)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return {"message": "Profile updated", "profile": svc.get_profile_dict(user_id)}


@router.delete("/me")
def delete_account(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = UserProfileService(db)
    svc.delete_user(user_id)
    return {"message": "Account deleted"}


@router.get("/me/conversation")
def get_conversation_history(
    query: str = "",
    limit: int = 20,
    user_id: str = Depends(get_current_user),
):
    conv_svc = ConversationMemoryService()
    messages = conv_svc.get_recent_context(user_id, query=query, limit=limit)
    return {"messages": messages}
