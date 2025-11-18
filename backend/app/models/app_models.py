from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:  # pragma: no cover
    from .dns import Domain


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    agent_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    app_instances: Mapped[List["AppInstance"]] = relationship(
        "AppInstance", back_populates="server", cascade="all, delete-orphan"
    )


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    default_image: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    instances: Mapped[List["AppInstance"]] = relationship(
        "AppInstance", back_populates="application", cascade="all, delete-orphan"
    )


class AppInstance(Base):
    __tablename__ = "app_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    app_id: Mapped[int] = mapped_column(Integer, ForeignKey("applications.id"), nullable=False)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="creating")
    main_domain_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("domains.id"), nullable=True
    )
    internal_container_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    docker_image: Mapped[str] = mapped_column(String, nullable=False)
    docker_port: Mapped[int] = mapped_column(Integer, default=80)
    replicas: Mapped[int] = mapped_column(Integer, default=1)
    env_vars: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    application: Mapped[Application] = relationship("Application", back_populates="instances")
    server: Mapped[Server] = relationship("Server", back_populates="app_instances")
    main_domain: Mapped[Optional["Domain"]] = relationship("Domain", foreign_keys=[main_domain_id])
    environment_variables: Mapped[List["AppEnvironmentVariable"]] = relationship(
        "AppEnvironmentVariable", back_populates="app_instance", cascade="all, delete-orphan"
    )
    domain_mappings: Mapped[List["AppDomainMapping"]] = relationship(
        "AppDomainMapping", back_populates="app_instance", cascade="all, delete-orphan"
    )


class AppEnvironmentVariable(Base):
    __tablename__ = "app_environment_variables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    app_instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_instances.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)

    app_instance: Mapped[AppInstance] = relationship("AppInstance", back_populates="environment_variables")


class AppDomainMapping(Base):
    __tablename__ = "app_domain_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    app_instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_instances.id"), nullable=False, index=True
    )
    domain_id: Mapped[int] = mapped_column(Integer, ForeignKey("domains.id"), nullable=False, index=True)
    subdomain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    app_instance: Mapped[AppInstance] = relationship("AppInstance", back_populates="domain_mappings")
    domain: Mapped["Domain"] = relationship("Domain")
