from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from src.api.deps import get_current_user, get_alert_service
from src.services.alert_service import AlertService

router = APIRouter()


class CreateAlertRequest(BaseModel):
    ticker: str
    alert_type: str       # price_above | price_below | volume_spike | news
    threshold: float


class UpdateAlertRequest(BaseModel):
    ticker: Optional[str] = None
    alert_type: Optional[str] = None
    threshold: Optional[float] = None
    active: Optional[bool] = None


@router.get("/")
async def list_alerts(
    active_only: bool = False,
    user_id: str = Depends(get_current_user),
    svc: AlertService = Depends(get_alert_service),
):
    alerts = svc.get_alerts(user_id, active_only=active_only)
    return {
        "alerts": [
            {
                "id": a.id,
                "ticker": a.ticker,
                "alert_type": a.alert_type,
                "threshold": a.threshold,
                "active": a.active,
                "triggered": a.triggered,
            }
            for a in alerts
        ]
    }


@router.post("/")
async def create_alert(
    body: CreateAlertRequest,
    user_id: str = Depends(get_current_user),
    svc: AlertService = Depends(get_alert_service),
):
    alert = svc.create_alert(user_id, body.ticker, body.alert_type, body.threshold)
    return {
        "id": alert.id,
        "ticker": alert.ticker,
        "alert_type": alert.alert_type,
        "threshold": alert.threshold,
    }


@router.put("/{alert_id}")
async def update_alert(
    alert_id: str,
    body: UpdateAlertRequest,
    user_id: str = Depends(get_current_user),
    svc: AlertService = Depends(get_alert_service),
):
    alert = svc.get_alert(alert_id)
    if not alert or alert.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    updated = svc.update_alert(alert_id, **updates)
    return {"message": "Alert updated", "alert_id": alert_id}


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    user_id: str = Depends(get_current_user),
    svc: AlertService = Depends(get_alert_service),
):
    alert = svc.get_alert(alert_id)
    if not alert or alert.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    svc.delete_alert(alert_id)
    return {"message": "Alert deleted"}
