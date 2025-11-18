from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from ..models.app_models import Server, ServerMetricSnapshot

logger = logging.getLogger(__name__)


def list_servers(db: Session) -> list[Server]:
    return db.query(Server).order_by(Server.created_at.desc()).all()


def get_server(db: Session, server_id: int) -> Optional[Server]:
    return db.get(Server, server_id)


def create_server(db: Session, data: Dict[str, Any]) -> Server:
    server = Server(**data)
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


def update_server(db: Session, server: Server, data: Dict[str, Any]) -> Server:
    for key, value in data.items():
        setattr(server, key, value)
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


def delete_server(db: Session, server: Server) -> None:
    db.delete(server)
    db.commit()


def _agent_get(url: str, headers: dict[str, str]) -> Dict[str, Any]:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def ping_server(db: Session, server: Server) -> Dict[str, Any]:
    if server.agent_url:
        try:
            result = _agent_get(
                f"{server.agent_url.rstrip('/')}/health",
                {"X-Agent-Token": server.agent_token or ""} if server.agent_token else {},
            )
        except requests.RequestException as exc:  # type: ignore[import-untyped]
            logger.warning("Failed to ping server %s: %s", server.name, exc)
            return {"status": "error", "detail": str(exc)}
    else:
        result = {"status": "ok", "mode": "local"} if server.is_master else {"status": "unknown"}
    if result.get("status") == "ok":
        server.last_seen_at = datetime.utcnow()
        db.add(server)
        db.commit()
    return result


def collect_metrics(db: Session, server: Server) -> Optional[ServerMetricSnapshot]:
    metrics: Optional[Dict[str, Any]] = None
    if server.agent_url:
        try:
            metrics = _agent_get(
                f"{server.agent_url.rstrip('/')}/metrics",
                {"X-Agent-Token": server.agent_token or ""} if server.agent_token else {},
            )
        except requests.RequestException as exc:  # type: ignore[import-untyped]
            logger.warning("Failed to collect metrics for %s: %s", server.name, exc)
            return None
    elif server.is_master:
        try:
            import psutil  # type: ignore

            metrics = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "docker_running_containers": 0,
                "docker_total_containers": 0,
            }
        except Exception as exc:  # pragma: no cover
            logger.debug("Local metrics unavailable: %s", exc)
            metrics = None

    if not metrics:
        return None

    snapshot = ServerMetricSnapshot(
        server_id=server.id,
        cpu_percent=metrics.get("cpu_percent", 0.0),
        memory_percent=metrics.get("memory_percent", 0.0),
        disk_percent=metrics.get("disk_percent", 0.0),
        docker_running_containers=int(metrics.get("docker_running_containers", 0)),
        docker_total_containers=int(metrics.get("docker_total_containers", 0)),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
