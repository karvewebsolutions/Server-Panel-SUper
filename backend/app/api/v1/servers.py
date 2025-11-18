from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import AppInstance, ServerMetricSnapshot
from ...schemas.server_schemas import (
    ServerCreate,
    ServerDetail,
    ServerMetricSnapshotRead,
    ServerSummary,
    ServerUpdate,
)
from ...services import server_service

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("/", response_model=List[ServerSummary])
def list_servers(db: Session = Depends(get_db)):
    servers = server_service.list_servers(db)
    summaries: list[ServerSummary] = []
    for server in servers:
        latest_metric = server.metric_snapshots[0] if server.metric_snapshots else None
        summary = ServerSummary.model_validate(server, from_attributes=True)
        summaries.append(summary.model_copy(update={"latest_metric": latest_metric}))
    return summaries


@router.post("/", response_model=ServerSummary, status_code=status.HTTP_201_CREATED)
def create_server(payload: ServerCreate, db: Session = Depends(get_db)):
    server = server_service.create_server(db, payload.model_dump())
    summary = ServerSummary.model_validate(server, from_attributes=True)
    return summary.model_copy(update={"latest_metric": None})


@router.get("/{server_id}", response_model=ServerDetail)
def get_server(server_id: int, db: Session = Depends(get_db)):
    server = server_service.get_server(db, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    metrics = (
        db.query(ServerMetricSnapshot)
        .filter(ServerMetricSnapshot.server_id == server.id)
        .order_by(ServerMetricSnapshot.created_at.desc())
        .limit(5)
        .all()
    )
    detail = ServerDetail.model_validate(server, from_attributes=True)
    return detail.model_copy(update={"metrics": metrics})


@router.put("/{server_id}", response_model=ServerDetail)
def update_server(server_id: int, payload: ServerUpdate, db: Session = Depends(get_db)):
    server = server_service.get_server(db, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    updated = server_service.update_server(db, server, payload.model_dump(exclude_unset=True))
    metrics = (
        db.query(ServerMetricSnapshot)
        .filter(ServerMetricSnapshot.server_id == server.id)
        .order_by(ServerMetricSnapshot.created_at.desc())
        .limit(5)
        .all()
    )
    detail = ServerDetail.model_validate(updated, from_attributes=True)
    return detail.model_copy(update={"metrics": metrics})


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(server_id: int, db: Session = Depends(get_db)):
    server = server_service.get_server(db, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    attached = db.query(AppInstance).filter(AppInstance.server_id == server.id).count()
    if attached:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server has attached applications",
        )
    server_service.delete_server(db, server)


@router.post("/{server_id}/ping")
def ping_server(server_id: int, db: Session = Depends(get_db)):
    server = server_service.get_server(db, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return server_service.ping_server(db, server)


@router.get("/{server_id}/metrics", response_model=List[ServerMetricSnapshotRead])
def get_metrics(
    server_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    server = server_service.get_server(db, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    metrics = (
        db.query(ServerMetricSnapshot)
        .filter(ServerMetricSnapshot.server_id == server_id)
        .order_by(ServerMetricSnapshot.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return metrics
