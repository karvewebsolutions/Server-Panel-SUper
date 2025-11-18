from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import BackupPolicy
from ..services.backup_service import BackupService

logger = logging.getLogger(__name__)


def run_scheduled_backups() -> None:
    with next(get_db()) as db:  # type: Session
        service = BackupService(db)
        policies = db.query(BackupPolicy).filter(BackupPolicy.is_enabled.is_(True)).all()
        for policy in policies:
            try:
                if policy.scope_type == "app_instance" and policy.scope_id:
                    service.run_backup_for_app_instance(policy.scope_id, policy_id=policy.id)
                else:
                    logger.info("Skipping unsupported policy scope %s", policy.scope_type)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Scheduled backup failed for policy %s: %s", policy.id, exc)


def apply_all_retention_policies() -> None:
    with next(get_db()) as db:  # type: Session
        service = BackupService(db)
        policies = db.query(BackupPolicy).filter(BackupPolicy.retain_last.isnot(None)).all()
        for policy in policies:
            try:
                service.apply_retention_policy(policy)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Retention application failed for policy %s: %s", policy.id, exc)
