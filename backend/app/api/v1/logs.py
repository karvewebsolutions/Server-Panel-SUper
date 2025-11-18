from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import ActivityLog, SuspiciousLoginAttempt
from ...schemas.monitoring_schemas import ActivityLogRead, SuspiciousLoginAttemptRead
from ...services import logs_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/app/{app_instance_id}")
def get_app_logs(app_instance_id: int, tail: int = 200, db: Session = Depends(get_db)):
    try:
        logs = logs_service.get_app_instance_logs(db, app_instance_id, tail=tail)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"logs": logs}


@router.get("/activity", response_model=List[ActivityLogRead])
def list_activity_logs(
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
    if user_id:
        query = query.filter(ActivityLog.user_id == user_id)
    if action:
        query = query.filter(ActivityLog.action == action)
    return query.all()


@router.get("/security/suspicious-logins", response_model=List[SuspiciousLoginAttemptRead])
def list_suspicious_logins(
    username: Optional[str] = Query(None),
    ip: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(SuspiciousLoginAttempt).order_by(
        SuspiciousLoginAttempt.created_at.desc()
    )
    if username:
        query = query.filter(SuspiciousLoginAttempt.username == username)
    if ip:
        query = query.filter(SuspiciousLoginAttempt.ip_address == ip)
    return query.all()
