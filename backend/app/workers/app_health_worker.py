from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import AppInstance
from ..services.monitoring_service import MonitoringService

logger = logging.getLogger(__name__)


def run_app_health_checks() -> None:
    with next(get_db()) as db:  # type: Session
        monitor = MonitoringService(db)
        app_instances = db.query(AppInstance).all()
        for app_instance in app_instances:
            try:
                monitor.evaluate_app_instance(app_instance)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "App health check failed for %s: %s", app_instance.display_name, exc
                )
        try:
            monitor.evaluate_ssl_expiry()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("SSL expiry evaluation failed: %s", exc)
