from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import Application, AppInstance, Domain, Server
from ...schemas.app_schemas import (
    AppInstanceCreate,
    AppInstanceRead,
    ApplicationCreate,
    ApplicationRead,
)
from ...services.app_blueprints import get_app_blueprint, list_app_blueprints
from ...services.deployment_engine import DeploymentEngine

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
    query = db.query(AppInstance)
    if server_id is not None:
        query = query.filter(AppInstance.server_id == server_id)
    if status_filter:
        query = query.filter(AppInstance.status == status_filter)
    if user_id:
        query = query.join(Application).filter(Application.created_by_user_id == user_id)
    return query.all()


@router.post("/instances", response_model=AppInstanceRead, status_code=status.HTTP_201_CREATED)
def create_app_instance(payload: AppInstanceCreate, db: Session = Depends(get_db)):
    application = db.get(Application, payload.app_id)
    server = db.get(Server, payload.server_id)
    if not application or not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application or server not found")

    app_type = payload.app_type or application.type
    blueprint = get_app_blueprint(app_type)
    config = payload.config or {}
    docker_image = config.get("docker_image") or application.default_image or blueprint.get("docker_image")
    if not docker_image:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Docker image not specified")
    docker_port = config.get("docker_port") or blueprint.get("docker_port") or 80
    env_vars = config.get("env_vars", {})

    domains: List[Domain] = []
    for domain_name in payload.domains:
        domain = db.query(Domain).filter(Domain.domain_name == domain_name).first()
        if not domain:
            domain = Domain(
                domain_name=domain_name,
                provider_type="powerdns",
                auto_ssl_enabled=True,
                auto_dns_enabled=True,
            )
            db.add(domain)
            db.commit()
            db.refresh(domain)
        domains.append(domain)

    main_domain_id = domains[0].id if domains else None
    extra_ids = [d.id for d in domains[1:]] if len(domains) > 1 else None
    internal_container_name = (
        config.get("container_name")
        or f"cp-app-{application.slug}-{server.id}-{uuid4().hex[:8]}"
    )

    app_instance = AppInstance(
        app_id=application.id,
        server_id=server.id,
        display_name=payload.display_name,
        status="creating",
        main_domain_id=main_domain_id,
        extra_domain_ids=extra_ids,
        internal_container_name=internal_container_name,
        docker_image=docker_image,
        docker_port=docker_port,
        env_vars=env_vars,
    )
    db.add(app_instance)
    db.commit()
    db.refresh(app_instance)

    try:
        app_instance = engine.deploy_app_instance(app_instance.id)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return app_instance


@router.post("/instances/{instance_id}/stop")
def stop_app_instance(instance_id: int):
    engine.stop_app_instance(instance_id)
    return {"status": "stopped"}


@router.post("/instances/{instance_id}/restart", response_model=AppInstanceRead)
def restart_app_instance(instance_id: int):
    return engine.restart_app_instance(instance_id)


@router.get("/instances/{instance_id}/logs")
def get_app_logs(instance_id: int, tail: int = 200):
    logs = engine.get_app_logs(instance_id, tail=tail)
    return {"logs": logs}
