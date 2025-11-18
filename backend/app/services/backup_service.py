from __future__ import annotations

import hashlib
import logging
import os
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..models.app_models import AppInstance
from ..models.backup_models import BackupJob, BackupPolicy, BackupSnapshot, BackupTarget
from .backup_target_base import BackupTargetHandler
from .backup_target_local import LocalBackupTargetHandler
from .backup_target_s3 import S3BackupTargetHandler
from .backup_target_sftp import SFTPBackupTargetHandler

logger = logging.getLogger(__name__)


def _sha256_checksum(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_app_instance_backup_tar(app_instance: AppInstance) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix=f"app-{app_instance.id}-backup-"))
    content_dir = temp_dir / "data"
    content_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = content_dir / "manifest.txt"
    manifest_path.write_text(
        f"Backup for app instance {app_instance.id}\n"
        f"Name: {app_instance.display_name}\n"
        f"Image: {app_instance.docker_image}\n"
        "TODO: include application data and database dumps.\n",
        encoding="utf-8",
    )

    tar_path = temp_dir / f"app_instance_{app_instance.id}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as archive:
        archive.add(content_dir, arcname=f"app_instance_{app_instance.id}")
    return tar_path


class BackupService:
    def __init__(self, db: Session):
        self.db = db

    def get_target_handler(self, target: BackupTarget) -> BackupTargetHandler:
        if target.type == "local":
            base_path = target.config_json.get("base_path", "/backups")
            return LocalBackupTargetHandler(base_path)
        if target.type == "s3":
            return S3BackupTargetHandler(target.config_json)
        if target.type == "sftp":
            return SFTPBackupTargetHandler(target.config_json)
        raise ValueError(f"Unsupported backup target type: {target.type}")

    def _resolve_policy(self, app_instance_id: int, policy_id: Optional[int]) -> Optional[BackupPolicy]:
        if policy_id:
            policy = self.db.get(BackupPolicy, policy_id)
            if not policy:
                raise ValueError("Backup policy not found")
            return policy
        return (
            self.db.query(BackupPolicy)
            .filter(
                BackupPolicy.scope_type == "app_instance",
                BackupPolicy.scope_id == app_instance_id,
                BackupPolicy.is_enabled.is_(True),
            )
            .order_by(BackupPolicy.created_at.desc())
            .first()
        )

    def _resolve_target(
        self, policy: Optional[BackupPolicy], target_override: Optional[int]
    ) -> BackupTarget:
        if target_override:
            target = self.db.get(BackupTarget, target_override)
            if not target:
                raise ValueError("Backup target not found")
            return target
        if policy:
            target = policy.target or self.db.get(BackupTarget, policy.backup_target_id)
            if target:
                return target
        default_target = (
            self.db.query(BackupTarget).filter(BackupTarget.is_default.is_(True)).first()
        )
        if default_target:
            return default_target
        raise ValueError("No backup target configured")

    def _create_job(
        self,
        policy: Optional[BackupPolicy],
        scope_type: str,
        scope_id: int,
        target: BackupTarget,
    ) -> BackupJob:
        job = BackupJob(
            policy_id=policy.id if policy else None,
            scope_type=scope_type,
            scope_id=scope_id,
            backup_target_id=target.id,
            status="pending",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def run_backup_for_app_instance(
        self,
        app_instance_id: int,
        policy_id: Optional[int] = None,
        target_override: Optional[int] = None,
    ) -> BackupJob:
        app_instance = self.db.get(AppInstance, app_instance_id)
        if not app_instance:
            raise ValueError("AppInstance not found")

        policy = self._resolve_policy(app_instance_id, policy_id)
        target = self._resolve_target(policy, target_override)
        handler = self.get_target_handler(target)

        job = self._create_job(policy, "app_instance", app_instance_id, target)

        try:
            job.status = "running"
            job.started_at = datetime.utcnow()
            self.db.add(job)
            self.db.commit()

            tar_path = create_app_instance_backup_tar(app_instance)
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            remote_subpath = f"app_instance/{app_instance.id}/{timestamp}.tar.gz"
            location_uri = handler.upload(str(tar_path), remote_subpath)
            size_bytes = os.path.getsize(tar_path)
            checksum = _sha256_checksum(tar_path)

            snapshot = BackupSnapshot(
                job_id=job.id,
                scope_type="app_instance",
                scope_id=app_instance.id,
                location_uri=location_uri,
                size_bytes=size_bytes,
                checksum=checksum,
            )
            self.db.add(snapshot)
            job.status = "success"
            job.finished_at = datetime.utcnow()
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            self.db.refresh(snapshot)
            return job
        except Exception as exc:  # pylint: disable=broad-except
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = datetime.utcnow()
            self.db.add(job)
            self.db.commit()
            logger.error("Backup job %s failed: %s", job.id, exc)
            raise
        finally:
            try:
                if "tar_path" in locals():
                    Path(tar_path).unlink(missing_ok=True)
                    temp_dir = Path(tar_path).parent
                    if temp_dir.exists():
                        for item in temp_dir.iterdir():
                            if item.exists():
                                item.unlink(missing_ok=True)
                        temp_dir.rmdir()
            except Exception:  # pylint: disable=broad-except
                logger.debug("Failed to clean up temp backup files", exc_info=True)

    def list_backups_for_app_instance(self, app_instance_id: int) -> list[BackupSnapshot]:
        return (
            self.db.query(BackupSnapshot)
            .filter(
                BackupSnapshot.scope_type == "app_instance",
                BackupSnapshot.scope_id == app_instance_id,
            )
            .order_by(BackupSnapshot.created_at.desc())
            .all()
        )

    def restore_app_instance_from_backup(self, app_instance_id: int, snapshot_id: int) -> None:
        snapshot = self.db.get(BackupSnapshot, snapshot_id)
        if not snapshot or snapshot.scope_type != "app_instance" or snapshot.scope_id != app_instance_id:
            raise ValueError("Snapshot does not belong to this app instance")
        job = snapshot.job or self.db.get(BackupJob, snapshot.job_id)
        if not job:
            raise ValueError("Backup job missing for snapshot")
        target = job.target or self.db.get(BackupTarget, job.backup_target_id)
        if not target:
            raise ValueError("Backup target missing for snapshot")

        handler = self.get_target_handler(target)
        temp_dir = Path(tempfile.mkdtemp(prefix=f"app-{app_instance_id}-restore-"))
        temp_file = temp_dir / "restore.tar.gz"
        try:
            handler.download(snapshot.location_uri, str(temp_file))
            if snapshot.checksum:
                downloaded_checksum = _sha256_checksum(temp_file)
                if downloaded_checksum != snapshot.checksum:
                    raise ValueError("Downloaded snapshot checksum mismatch")

            raise ValueError(
                "Restore workflow for app instances is not implemented yet; snapshot download verified"
            )
        finally:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                if temp_dir.exists():
                    temp_dir.rmdir()
            except Exception:  # pylint: disable=broad-except
                logger.debug("Failed to clean up temp restore files", exc_info=True)

    def run_manual_backup(
        self, scope_type: str, scope_id: int, target_id: Optional[int] = None
    ) -> BackupJob:
        if scope_type == "app_instance":
            return self.run_backup_for_app_instance(scope_id, target_override=target_id)
        raise ValueError(f"Unsupported scope for manual backup: {scope_type}")

    def apply_retention_policy(self, policy: BackupPolicy) -> None:
        if not policy.retain_last:
            return
        snapshots = (
            self.db.query(BackupSnapshot)
            .join(BackupJob, BackupJob.id == BackupSnapshot.job_id)
            .filter(BackupJob.policy_id == policy.id)
            .order_by(BackupSnapshot.created_at.desc())
            .all()
        )
        if len(snapshots) <= policy.retain_last:
            return
        for snapshot in snapshots[policy.retain_last :]:
            logger.info("Pruning snapshot %s for policy %s", snapshot.id, policy.id)
            self.db.delete(snapshot)
        self.db.commit()
