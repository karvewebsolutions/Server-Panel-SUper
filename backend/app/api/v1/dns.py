from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.dns import DNSProviderCredential, DNSRecord, Domain
from ...schemas.dns import (
    DNSProviderCredentialCreate,
    DNSProviderCredentialRead,
    DNSRecordCreate,
    DNSRecordRead,
    DomainCreate,
    DomainRead,
)
from ...services.dns.dns_manager import DNSManager

router = APIRouter(prefix="/dns", tags=["dns"])


@router.get("/providers", response_model=List[DNSProviderCredentialRead])
def list_providers(db: Session = Depends(get_db)):
    return db.query(DNSProviderCredential).all()


@router.post("/providers", response_model=DNSProviderCredentialRead, status_code=status.HTTP_201_CREATED)
def create_provider(
    payload: DNSProviderCredentialCreate, db: Session = Depends(get_db)
):
    provider = DNSProviderCredential(**payload.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = db.get(DNSProviderCredential, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    db.delete(provider)
    db.commit()


@router.get("/domains", response_model=List[DomainRead])
def list_domains(db: Session = Depends(get_db)):
    return db.query(Domain).all()


@router.post("/domains", response_model=DomainRead, status_code=status.HTTP_201_CREATED)
def create_domain(payload: DomainCreate, db: Session = Depends(get_db)):
    domain = Domain(**payload.model_dump())
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


@router.get("/domains/{domain_id}", response_model=DomainRead)
def get_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    return domain


@router.delete("/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    db.delete(domain)
    db.commit()


@router.get("/domains/{domain_id}/records", response_model=List[DNSRecordRead])
def list_domain_records(domain_id: int, db: Session = Depends(get_db)):
    return (
        db.query(DNSRecord)
        .filter(DNSRecord.domain_id == domain_id)
        .order_by(DNSRecord.created_at.desc())
        .all()
    )


@router.post(
    "/domains/{domain_id}/records",
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
    db.commit()
    db.refresh(record)
    manager = DNSManager(db)
    record.domain = domain
    provider = manager._get_provider(domain)
    if hasattr(provider, "create_record"):
        provider.create_record(record)
    return record


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: Session = Depends(get_db)):
    record = db.get(DNSRecord, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    domain = db.get(Domain, record.domain_id)
    manager = DNSManager(db)
    if domain:
        record.domain = domain
        provider = manager._get_provider(domain)
        if hasattr(provider, "delete_record"):
            provider.delete_record(record)
    db.delete(record)
    db.commit()


@router.post("/domains/{domain_id}/sync")
def sync_domain(domain_id: int, db: Session = Depends(get_db)):
    manager = DNSManager(db)
    try:
        records = manager.sync_domain(domain_id)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"status": "synced", "records": records}


@router.post("/domains/{domain_id}/verify")
def verify_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = db.get(Domain, domain_id)
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    manager = DNSManager(db)
    provider = manager._get_provider(domain)
    provider.ensure_zone(domain)
    return {"status": "verified"}
