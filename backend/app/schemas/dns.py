from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DNSProviderCredentialCreate(BaseModel):
    provider_name: str
    credentials_json: dict[str, Any] = Field(default_factory=dict)
    owner_user_id: int


class DNSProviderCredentialRead(DNSProviderCredentialCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DomainCreate(BaseModel):
    domain_name: str
    provider_type: str
    provider_credential_id: int | None = None
    auto_ssl_enabled: bool = True
    auto_dns_enabled: bool = True


class DomainRead(DomainCreate):
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
