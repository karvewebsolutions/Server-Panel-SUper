from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class BackupTargetBase(BaseModel):
    name: str
    type: str
    config_json: dict[str, Any]
    is_default: bool = False


class BackupTargetCreate(BackupTargetBase):
    pass


class BackupTargetRead(BackupTargetBase):
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BackupPolicyBase(BaseModel):
    name: str
    scope_type: str
    scope_id: Optional[int] = None
    schedule_cron: Optional[str] = None
    backup_target_id: int
    retain_last: Optional[int] = None
    is_enabled: bool = True


class BackupPolicyCreate(BackupPolicyBase):
    pass


class BackupPolicyUpdate(BaseModel):
    name: Optional[str] = None
    scope_type: Optional[str] = None
    scope_id: Optional[int] = None
    schedule_cron: Optional[str] = None
    backup_target_id: Optional[int] = None
    retain_last: Optional[int] = None
    is_enabled: Optional[bool] = None


class BackupPolicyRead(BackupPolicyBase):
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BackupJobRead(BaseModel):
    id: int
    policy_id: Optional[int] = None
    scope_type: str
    scope_id: int
    backup_target_id: int
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BackupSnapshotRead(BaseModel):
    id: int
    job_id: int
    scope_type: str
    scope_id: int
    location_uri: str
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    created_at: datetime
    job: Optional[BackupJobRead] = None

    class Config:
        from_attributes = True


class ManualBackupRequest(BaseModel):
    target_id: Optional[int] = None
    policy_id: Optional[int] = None


class RestoreRequest(BaseModel):
    snapshot_id: int
