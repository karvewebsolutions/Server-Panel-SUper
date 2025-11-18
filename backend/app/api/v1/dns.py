from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models.dns import DNSProviderCredential
from ...schemas.dns import (
    DNSProviderCredentialCreate,
    DNSProviderCredentialRead,
)

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
