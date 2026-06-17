from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.routes.auth import get_current_user
from app.backend.database.connection import get_db
from src.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


class CreateAlertRequest(BaseModel):
    ticker: str
    alert_type: str
    threshold: float


class UpdateAlertRequest(BaseModel):
    ticker: Optional[str] = None
    alert_type: Optional[str] = None
    threshold: Optional[float] = None
    active: Optional[bool] = None


@router.get("/")
def list_alerts(active_only: bool = False, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = AlertService(db)
    alerts = svc.get_alerts(user_id, active_only=active_only)
    return {
        "alerts": [
            {"id": a.id, "ticker": a.ticker, "alert_type": a.alert_type, "threshold": a.threshold, "active": a.active, "triggered": a.triggered}
            for a in alerts
        ]
    }


@router.post("/")
def create_alert(body: CreateAlertRequest, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = AlertService(db)
    alert = svc.create_alert(user_id, body.ticker, body.alert_type, body.threshold)
    return {"id": alert.id, "ticker": alert.ticker, "alert_type": alert.alert_type, "threshold": alert.threshold}


@router.put("/{alert_id}")
def update_alert(alert_id: str, body: UpdateAlertRequest, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = AlertService(db)
    alert = svc.get_alert(alert_id)
    if not alert or alert.user_id != user_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    svc.update_alert(alert_id, **updates)
    return {"message": "Alert updated", "alert_id": alert_id}


@router.delete("/{alert_id}")
def delete_alert(alert_id: str, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = AlertService(db)
    alert = svc.get_alert(alert_id)
    if not alert or alert.user_id != user_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    svc.delete_alert(alert_id)
    return {"message": "Alert deleted"}
