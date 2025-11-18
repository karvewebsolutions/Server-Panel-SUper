from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class DNSProviderCredential(Base):
    __tablename__ = "dns_provider_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    credentials_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    domains: Mapped[List["Domain"]] = relationship("Domain", back_populates="provider_credential")


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain_name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider_credential_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("dns_provider_credentials.id"), nullable=True
    )
    auto_ssl_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_dns_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_wildcard: Mapped[bool] = mapped_column(Boolean, default=False)
    base_domain_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("domains.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    provider_credential: Mapped[Optional[DNSProviderCredential]] = relationship(
        "DNSProviderCredential", back_populates="domains", lazy="joined"
    )
    records: Mapped[List["DNSRecord"]] = relationship(
        "DNSRecord", back_populates="domain", cascade="all, delete-orphan"
    )
    base_domain: Mapped[Optional["Domain"]] = relationship(
        "Domain",
        remote_side=[id],  # type: ignore[ListItem]
        back_populates="subdomains",
    )
    subdomains: Mapped[List["Domain"]] = relationship(
        "Domain",
        back_populates="base_domain",
        cascade="all, delete-orphan",
    )


class DNSRecord(Base):
    __tablename__ = "dns_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain_id: Mapped[int] = mapped_column(Integer, ForeignKey("domains.id"), nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    ttl: Mapped[int] = mapped_column(Integer, default=300)
    proxied: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    domain: Mapped[Domain] = relationship("Domain", back_populates="records")
