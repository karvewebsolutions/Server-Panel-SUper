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
