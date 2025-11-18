from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DomainBase(BaseModel):
    domain_name: str
    provider_type: str
    provider_credential_id: int | None = None
    auto_ssl_enabled: bool = True
    auto_dns_enabled: bool = True
    is_wildcard: bool = False
    base_domain_id: int | None = None


class DomainCreate(DomainBase):
    pass


class DomainRead(DomainBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DNSRecordCreate(BaseModel):
    record_type: str
    name: str
    value: str
    ttl: int = 300
    proxied: bool | None = None


class DNSRecordRead(DNSRecordCreate):
    id: int
    domain_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DomainDetailRead(DomainRead):
    records: list[DNSRecordRead] = Field(default_factory=list)


class SubdomainPreviewRequest(BaseModel):
    app_name: str


class SubdomainPreviewResponse(BaseModel):
    suggested_subdomain: str
