from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ..models import ActivityLog, AppInstance, Server
from .docker_service import DockerService


def get_app_instance_logs(db: Session, app_instance_id: int, tail: int = 200) -> str:
    app_instance = db.get(AppInstance, app_instance_id)
    if not app_instance:
        raise ValueError("AppInstance not found")
    server = db.get(Server, app_instance.server_id)
    if not server:
        raise ValueError("Server not found for AppInstance")
    docker = DockerService()
    return docker.get_logs(server, app_instance.internal_container_name, tail=tail)


def create_activity_log(
    db: Session, user_id: Optional[int], action: str, metadata: Optional[dict] = None
) -> ActivityLog:
    log = ActivityLog(user_id=user_id, action=action, metadata_json=metadata)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
