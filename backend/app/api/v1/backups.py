from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import BackupPolicy, BackupSnapshot, BackupTarget
from ...schemas.backup_schemas import (
    BackupJobRead,
    BackupPolicyCreate,
    BackupPolicyRead,
    BackupPolicyUpdate,
    BackupSnapshotRead,
    BackupTargetCreate,
    BackupTargetRead,
    ManualBackupRequest,
    RestoreRequest,
)
from ...services.backup_service import BackupService

router = APIRouter(tags=["backups"])


@router.get("/backup-targets", response_model=List[BackupTargetRead])
def list_backup_targets(db: Session = Depends(get_db)):
    return db.query(BackupTarget).order_by(BackupTarget.created_at.desc()).all()


@router.post(
    "/backup-targets",
    response_model=BackupTargetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_backup_target(payload: BackupTargetCreate, db: Session = Depends(get_db)):
    target = BackupTarget(**payload.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("/backup-targets/{target_id}", response_model=BackupTargetRead)
def get_backup_target(target_id: int, db: Session = Depends(get_db)):
    target = db.get(BackupTarget, target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup target not found")
    return target


@router.delete("/backup-targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backup_target(target_id: int, db: Session = Depends(get_db)):
    target = db.get(BackupTarget, target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup target not found")
    db.delete(target)
    db.commit()


@router.get("/backup-policies", response_model=List[BackupPolicyRead])
def list_backup_policies(db: Session = Depends(get_db)):
    return db.query(BackupPolicy).order_by(BackupPolicy.created_at.desc()).all()


@router.post(
    "/backup-policies",
    response_model=BackupPolicyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_backup_policy(payload: BackupPolicyCreate, db: Session = Depends(get_db)):
    target = db.get(BackupTarget, payload.backup_target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid backup target")
    policy = BackupPolicy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/backup-policies/{policy_id}", response_model=BackupPolicyRead)
def get_backup_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.get(BackupPolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup policy not found")
    return policy


@router.put("/backup-policies/{policy_id}", response_model=BackupPolicyRead)
def update_backup_policy(
    policy_id: int, payload: BackupPolicyUpdate, db: Session = Depends(get_db)
):
    policy = db.get(BackupPolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup policy not found")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(policy, key, value)
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/backup-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backup_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.get(BackupPolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup policy not found")
    db.delete(policy)
    db.commit()


@router.get(
    "/backups/app-instances/{app_instance_id}/snapshots",
    response_model=List[BackupSnapshotRead],
)
def list_app_instance_snapshots(app_instance_id: int, db: Session = Depends(get_db)):
    service = BackupService(db)
    snapshots: List[BackupSnapshot] = service.list_backups_for_app_instance(app_instance_id)
    return snapshots


@router.post(
    "/backups/app-instances/{app_instance_id}/run",
    response_model=BackupJobRead,
)
def run_app_instance_backup(
    app_instance_id: int,
    payload: ManualBackupRequest | None = None,
    db: Session = Depends(get_db),
):
    service = BackupService(db)
    try:
        if payload and payload.policy_id:
            job = service.run_backup_for_app_instance(
                app_instance_id, policy_id=payload.policy_id, target_override=payload.target_id
            )
        elif payload and payload.target_id:
            job = service.run_backup_for_app_instance(app_instance_id, target_override=payload.target_id)
        else:
            job = service.run_backup_for_app_instance(app_instance_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return job


@router.post("/backups/app-instances/{app_instance_id}/restore")
def restore_app_instance_backup(
    app_instance_id: int, payload: RestoreRequest, db: Session = Depends(get_db)
):
    service = BackupService(db)
    try:
        service.restore_app_instance_from_backup(app_instance_id, payload.snapshot_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "restore_scheduled"}
