from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ServerBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_master: bool = False
    agent_url: Optional[str] = None
    agent_token: Optional[str] = None
    location: Optional[str] = None
    is_active: bool = True


class ServerCreate(ServerBase):
    pass


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_master: Optional[bool] = None
    agent_url: Optional[str] = None
    agent_token: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class ServerMetricSnapshotRead(BaseModel):
    id: int
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    docker_running_containers: int
    docker_total_containers: int
    created_at: datetime

    class Config:
        from_attributes = True


class ServerRead(ServerBase):
    id: int
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServerSummary(ServerRead):
    latest_metric: Optional[ServerMetricSnapshotRead] = None


class ServerDetail(ServerRead):
    metrics: list[ServerMetricSnapshotRead] = Field(default_factory=list)
