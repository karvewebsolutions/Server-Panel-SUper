from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import AlertEvent, AlertRule
from ...schemas.monitoring_schemas import AlertEventRead, AlertRuleCreate, AlertRuleRead
from ...services.monitoring_service import MonitoringService
from ...services.auth import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=List[AlertEventRead])
def list_alerts(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None),
    is_acknowledged: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(AlertEvent).order_by(AlertEvent.created_at.desc()).limit(limit)
    if severity:
        query = query.filter(AlertEvent.severity == severity)
    if is_acknowledged is not None:
        query = query.filter(AlertEvent.is_acknowledged.is_(is_acknowledged))
    return query.all()


@router.post("/{alert_id}/ack", response_model=AlertEventRead)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    service = MonitoringService(db)
    try:
        return service.acknowledge_alert(alert_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")


@router.get("/rules", response_model=List[AlertRuleRead])
def list_rules(db: Session = Depends(get_db)):
    return (
        db.query(AlertRule)
        .order_by(AlertRule.created_at.desc())
        .all()
    )


@router.post("/rules", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rule = AlertRule(**payload.model_dump(), created_by_user_id=current_user.id)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/rules/{rule_id}", response_model=AlertRuleRead)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    db.delete(rule)
    db.commit()
