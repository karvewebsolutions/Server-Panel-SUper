from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class BackupTarget(Base):
    __tablename__ = "backup_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    policies: Mapped[list["BackupPolicy"]] = relationship(
        "BackupPolicy", back_populates="target", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["BackupJob"]] = relationship("BackupJob", back_populates="target")


class BackupPolicy(Base):
    __tablename__ = "backup_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    scope_type: Mapped[str] = mapped_column(String, nullable=False)
    scope_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    backup_target_id: Mapped[int] = mapped_column(Integer, ForeignKey("backup_targets.id"))
    retain_last: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    target: Mapped[BackupTarget] = relationship("BackupTarget", back_populates="policies")
    jobs: Mapped[list["BackupJob"]] = relationship("BackupJob", back_populates="policy")


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    policy_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("backup_policies.id"))
    scope_type: Mapped[str] = mapped_column(String, nullable=False)
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False)
    backup_target_id: Mapped[int] = mapped_column(Integer, ForeignKey("backup_targets.id"))
    status: Mapped[str] = mapped_column(String, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    policy: Mapped[Optional[BackupPolicy]] = relationship("BackupPolicy", back_populates="jobs")
    target: Mapped[BackupTarget] = relationship("BackupTarget", back_populates="jobs")
    snapshots: Mapped[list["BackupSnapshot"]] = relationship(
        "BackupSnapshot", back_populates="job", cascade="all, delete-orphan"
    )


class BackupSnapshot(Base):
    __tablename__ = "backup_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("backup_jobs.id"))
    scope_type: Mapped[str] = mapped_column(String, nullable=False)
    scope_id: Mapped[int] = mapped_column(Integer, nullable=False)
    location_uri: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped[BackupJob] = relationship("BackupJob", back_populates="snapshots")
