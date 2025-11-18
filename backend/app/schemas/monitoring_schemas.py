from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    name: str
    scope_type: str
    scope_id: Optional[int] = None
    rule_type: str
    threshold_value: Optional[float] = None
    is_enabled: bool = True


class AlertRuleRead(AlertRuleCreate):
    id: int
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertEventRead(BaseModel):
    id: int
    rule_id: int
    scope_type: str
    scope_id: Optional[int] = None
    message: str
    severity: str
    created_at: datetime
    is_acknowledged: bool
    acknowledged_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActivityLogRead(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    metadata_json: Optional[dict] = Field(default=None)
    created_at: datetime

    class Config:
        from_attributes = True


class SuspiciousLoginAttemptRead(BaseModel):
    id: int
    username: str
    ip_address: str
    user_agent: Optional[str] = None
    reason: str
    created_at: datetime

    class Config:
        from_attributes = True
