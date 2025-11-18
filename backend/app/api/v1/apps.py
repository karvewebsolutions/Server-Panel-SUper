from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from ...core.database import get_db
from ...models import AppDomainMapping, AppInstance, Application, Domain, Server
from ...schemas.app_schemas import (
    AppInstanceCreate,
    AppInstanceRead,
    AppInstanceDomainAttachRequest,
    ApplicationCreate,
    ApplicationRead,
    DomainMappingInput,
)
from ...services.app_blueprints import get_app_blueprint, list_app_blueprints
from ...services.deployment_engine import DeploymentEngine
from ...services.subdomain_service import SubdomainService

router = APIRouter(prefix="/apps", tags=["apps"])
engine = DeploymentEngine()


@router.get("/blueprints")
def blueprints():
    return list_app_blueprints()


@router.get("/", response_model=List[ApplicationRead])
def list_applications(db: Session = Depends(get_db)):
    return db.query(Application).all()


@router.post("/", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    application = Application(**payload.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/{app_id}", response_model=ApplicationRead)
def get_application(app_id: int, db: Session = Depends(get_db)):
    application = db.get(Application, app_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(app_id: int, db: Session = Depends(get_db)):
    application = db.get(Application, app_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    db.delete(application)
    db.commit()


@router.get("/instances", response_model=List[AppInstanceRead])
def list_app_instances(
    server_id: Optional[int] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    user_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(AppInstance).options(
        selectinload(AppInstance.domain_mappings).selectinload(AppDomainMapping.domain)
    )
    if server_id is not None:
        query = query.filter(AppInstance.server_id == server_id)
    if status_filter:
        query = query.filter(AppInstance.status == status_filter)
    if user_id:
        query = query.join(Application).filter(Application.created_by_user_id == user_id)
    return query.all()


@router.get("/instances/{instance_id}", response_model=AppInstanceRead)
def get_app_instance(instance_id: int, db: Session = Depends(get_db)):
    app_instance = _app_instance_with_domains(db, instance_id)
    if not app_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AppInstance not found")
    return app_instance


@router.post("/instances", response_model=AppInstanceRead, status_code=status.HTTP_201_CREATED)
def create_app_instance(payload: AppInstanceCreate, db: Session = Depends(get_db)):
    application = db.get(Application, payload.app_id)
    server = db.get(Server, payload.server_id)
    if not application or not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application or server not found")
    prepared_mappings, primary_domain_id = _prepare_domain_payloads(db, payload.domains)

    app_type = payload.app_type or application.type
    blueprint = get_app_blueprint(app_type)
    config = payload.config or {}
    docker_image = config.get("docker_image") or application.default_image or blueprint.get("docker_image")
    if not docker_image:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Docker image not specified")
    docker_port = config.get("docker_port") or blueprint.get("docker_port") or 80
    env_vars = config.get("env_vars", {})

    internal_container_name = (
        config.get("container_name")
        or f"cp-app-{application.slug}-{server.id}-{uuid4().hex[:8]}"
    )

    app_instance = AppInstance(
        app_id=application.id,
        server_id=server.id,
        display_name=payload.display_name,
        status="creating",
        main_domain_id=primary_domain_id,
        internal_container_name=internal_container_name,
        docker_image=docker_image,
        docker_port=docker_port,
        env_vars=env_vars,
    )
    db.add(app_instance)
    db.flush()
    _replace_domain_mappings(db, app_instance.id, prepared_mappings)
    db.commit()
    db.refresh(app_instance)

    try:
        engine.deploy_app_instance(app_instance.id)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    enriched = _app_instance_with_domains(db, app_instance.id)
    return enriched or app_instance


@router.post("/instances/{instance_id}/stop")
def stop_app_instance(instance_id: int):
    engine.stop_app_instance(instance_id)
    return {"status": "stopped"}


@router.post("/instances/{instance_id}/restart", response_model=AppInstanceRead)
def restart_app_instance(instance_id: int, db: Session = Depends(get_db)):
    updated = engine.restart_app_instance(instance_id)
    refreshed = _app_instance_with_domains(db, instance_id)
    return refreshed or updated


@router.get("/instances/{instance_id}/logs")
def get_app_logs(instance_id: int, tail: int = 200):
    logs = engine.get_app_logs(instance_id, tail=tail)
    return {"logs": logs}


@router.post("/instances/{instance_id}/domains", response_model=AppInstanceRead)
def attach_app_domains(
    instance_id: int,
    payload: AppInstanceDomainAttachRequest,
    db: Session = Depends(get_db),
):
    app_instance = db.get(AppInstance, instance_id)
    if not app_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AppInstance not found")
    prepared_mappings, primary_domain_id = _prepare_domain_payloads(db, payload.domains)
    app_instance.main_domain_id = primary_domain_id
    db.flush()
    _replace_domain_mappings(db, app_instance.id, prepared_mappings)
    db.commit()
    try:
        engine.restart_app_instance(app_instance.id)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    refreshed = _app_instance_with_domains(db, app_instance.id)
    return refreshed or app_instance


def _prepare_domain_payloads(
    db: Session, domain_inputs: List[DomainMappingInput] | None
) -> tuple[List[dict], int | None]:
    mappings = domain_inputs or []
    if not mappings:
        return [], None
    primary_count = sum(1 for item in mappings if item.is_primary)
    if primary_count > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple primary domains selected",
        )
    prepared: List[dict] = []
    for item in mappings:
        domain = db.get(Domain, item.domain_id)
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain {item.domain_id} not found",
            )
        normalized_sub = SubdomainService.normalize_subdomain(item.subdomain)
        prepared.append(
            {
                "domain_id": domain.id,
                "subdomain": normalized_sub or None,
                "is_primary": item.is_primary,
            }
        )
    if primary_count == 0 and prepared:
        prepared[0]["is_primary"] = True
    primary_domain_id = next(
        (entry["domain_id"] for entry in prepared if entry["is_primary"]),
        None,
    )
    return prepared, primary_domain_id


def _replace_domain_mappings(
    db: Session, app_instance_id: int, mappings: List[dict]
) -> None:
    db.query(AppDomainMapping).filter(
        AppDomainMapping.app_instance_id == app_instance_id
    ).delete(synchronize_session=False)
    for mapping in mappings:
        db.add(
            AppDomainMapping(
                app_instance_id=app_instance_id,
                domain_id=mapping["domain_id"],
                subdomain=mapping["subdomain"],
                is_primary=mapping["is_primary"],
            )
        )
    db.flush()


def _app_instance_with_domains(db: Session, instance_id: int) -> AppInstance | None:
    return (
        db.query(AppInstance)
        .options(
            selectinload(AppInstance.domain_mappings).selectinload(AppDomainMapping.domain)
        )
        .filter(AppInstance.id == instance_id)
        .first()
    )
