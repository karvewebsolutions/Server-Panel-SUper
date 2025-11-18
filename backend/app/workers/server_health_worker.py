from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import Server
from ..services import server_service

logger = logging.getLogger(__name__)


def run_server_health_checks() -> None:
    with next(get_db()) as db:  # type: Session
        servers = db.query(Server).filter(Server.is_active.is_(True)).all()
        for server in servers:
            try:
                server_service.ping_server(db, server)
                server_service.collect_metrics(db, server)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Health check failed for %s: %s", server.name, exc)
