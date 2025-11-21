from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import AppDomainMapping, AppInstance
from ...models.dns import DNSRecord, Domain
from ...schemas.domain_schemas import (
    DNSRecordCreate,
    DNSRecordRead,
    DomainCreate,
    DomainDetailRead,
    DomainRead,
    SubdomainPreviewRequest,
    SubdomainPreviewResponse,
)
from ...services.dns.dns_manager import DNSManager
from ...services.subdomain_service import SubdomainService

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("/", response_model=List[DomainRead])
def list_domains(db: Session = Depends(get_db)):
    return db.query(Domain).order_by(Domain.created_at.desc()).all()


@router.post("/", response_model=DomainRead, status_code=status.HTTP_201_CREATED)
def create_domain(payload: DomainCreate, db: Session = Depends(get_db)):
    normalized_name = SubdomainService.normalize_domain(payload.domain_name)
    existing = (
        db.query(Domain).filter(Domain.domain_name == normalized_name).one_or_none()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Domain already exists")
    data = payload.model_dump()
    data["domain_name"] = normalized_name
    domain = Domain(**data)
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


@router.get("/{domain_id}", response_model=DomainDetailRead)
def get_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    domain_data = DomainRead.model_validate(domain)
    records = [DNSRecordRead.model_validate(record) for record in domain.records]
    return DomainDetailRead(**domain_data.model_dump(), records=records)


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    instance_usage = (
        db.query(AppInstance)
        .filter(AppInstance.main_domain_id == domain_id)
        .first()
    )
    mapping_exists = bool(
        db.query(exists().where(AppDomainMapping.domain_id == domain_id)).scalar()
    )
    if instance_usage or mapping_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain is mapped to an app instance",
        )
    db.delete(domain)
    db.commit()


@router.get("/{domain_id}/records", response_model=List[DNSRecordRead])
def list_domain_records(domain_id: int, db: Session = Depends(get_db)):
    return (
        db.query(DNSRecord)
        .filter(DNSRecord.domain_id == domain_id)
        .order_by(DNSRecord.created_at.desc())
        .all()
    )


@router.post(
    "/{domain_id}/records",
    response_model=DNSRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_domain_record(
    domain_id: int, payload: DNSRecordCreate, db: Session = Depends(get_db)
):
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    record = DNSRecord(domain_id=domain_id, **payload.model_dump())
    db.add(record)
    manager = DNSManager(db)
    record.domain = domain
    provider = manager._get_provider(domain)
    try:
        if hasattr(provider, "create_record"):
            provider.create_record(record)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(record)
    return record


@router.delete("/{domain_id}/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain_record(
    domain_id: int, record_id: int, db: Session = Depends(get_db)
):
    record = (
        db.query(DNSRecord)
        .filter(DNSRecord.domain_id == domain_id, DNSRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    domain = db.get(Domain, domain_id)
    if domain:
        manager = DNSManager(db)
        record.domain = domain
        provider = manager._get_provider(domain)
        if hasattr(provider, "delete_record"):
            provider.delete_record(record)
    db.delete(record)
    db.commit()


@router.post("/{domain_id}/subdomain-preview", response_model=SubdomainPreviewResponse)
def preview_subdomain(
    domain_id: int,
    payload: SubdomainPreviewRequest,
    db: Session = Depends(get_db),
):
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    suggestion = SubdomainService.generate_subdomain_from_app_name(payload.app_name)
    return SubdomainPreviewResponse(suggested_subdomain=suggestion)


@router.post("/{domain_id}/sync")
def sync_domain(domain_id: int, db: Session = Depends(get_db)):
    manager = DNSManager(db)
    try:
        records = manager.sync_domain(domain_id)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"status": "synced", "records": records}


@router.post("/{domain_id}/verify")
def verify_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    manager = DNSManager(db)
    provider = manager._get_provider(domain)
    provider.ensure_zone(domain)
    return {"status": "verified"}
