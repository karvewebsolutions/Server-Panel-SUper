from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ApplicationBase(BaseModel):
    name: str
    slug: str
    type: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    default_image: Optional[str] = None
    created_by_user_id: int


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationRead(ApplicationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppInstanceCreate(BaseModel):
    app_id: int
    server_id: int
    display_name: str
    domains: List[str] = Field(default_factory=list)
    app_type: Optional[str] = None
    config: Optional[dict[str, Any]] = None


class AppInstanceRead(BaseModel):
    id: int
    app_id: int
    server_id: int
    display_name: str
    status: str
    main_domain_id: Optional[int]
    extra_domain_ids: Optional[list[int]]
    internal_container_name: str
    docker_image: str
    docker_port: int
    replicas: int
    env_vars: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppEnvironmentVariableRead(BaseModel):
    id: int
    key: str
    value: str
    is_secret: bool

    class Config:
        from_attributes = True
