from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from .domain_schemas import DomainRead


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


class ServerBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_master: bool = False
    agent_url: Optional[str] = None
    agent_token: Optional[str] = None
    location: Optional[str] = None


class ServerCreate(ServerBase):
    pass


class ServerRead(ServerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DomainMappingInput(BaseModel):
    domain_id: int
    subdomain: Optional[str] = None
    is_primary: bool = False


class AppDomainMappingRead(BaseModel):
    id: int
    domain_id: int
    subdomain: Optional[str]
    is_primary: bool
    created_at: datetime
    domain: Optional[DomainRead] = None

    class Config:
        from_attributes = True


class AppInstanceCreate(BaseModel):
    app_id: int
    server_id: int
    display_name: str
    domains: List[DomainMappingInput] = Field(default_factory=list)
    app_type: Optional[str] = None
    config: Optional[dict[str, Any]] = None


class AppInstanceRead(BaseModel):
    id: int
    app_id: int
    server_id: int
    display_name: str
    status: str
    main_domain_id: Optional[int]
    internal_container_name: str
    docker_image: str
    docker_port: int
    replicas: int
    env_vars: dict
    created_at: datetime
    updated_at: datetime
    domain_mappings: List[AppDomainMappingRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AppEnvironmentVariableRead(BaseModel):
    id: int
    key: str
    value: str
    is_secret: bool

    class Config:
        from_attributes = True


class AppInstanceDomainAttachRequest(BaseModel):
    domains: List[DomainMappingInput]
