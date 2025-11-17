from __future__ import annotations

import logging
from typing import List

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models import AppInstance, Application, Domain, Server
from .dns.dns_manager import DNSManager
from .docker_service import DockerService
from .traefik_service import TraefikLabelBuilder

logger = logging.getLogger(__name__)


class DeploymentEngine:
    def __init__(self, db_factory=SessionLocal):
        self.db_factory = db_factory
        self.docker_service = DockerService()

    def _get_db(self) -> Session:
        return self.db_factory()

    def deploy_app_instance(self, app_instance_id: int) -> AppInstance:
        db = self._get_db()
        try:
            app_instance = db.get(AppInstance, app_instance_id)
            if not app_instance:
                raise ValueError(f"AppInstance {app_instance_id} not found")
            application = db.get(Application, app_instance.app_id)
            server = db.get(Server, app_instance.server_id)
            if not application or not server:
                raise ValueError("Application or Server missing for deployment")

            domains: List[Domain] = []
            if app_instance.main_domain_id:
                main_domain = db.get(Domain, app_instance.main_domain_id)
                if main_domain:
                    domains.append(main_domain)
            if app_instance.extra_domain_ids:
                extra_domains = (
                    db.query(Domain)
                    .filter(Domain.id.in_(app_instance.extra_domain_ids))
                    .all()
                )
                domains.extend(extra_domains)

            dns_manager = DNSManager(db)
            for domain in domains:
                try:
                    dns_manager.create_dns_for_deployment(
                        app_instance, domain, subdomains=[]
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("DNS provisioning failed for %s: %s", domain.domain_name, exc)

            domain_names = [d.domain_name for d in domains]
            labels = TraefikLabelBuilder.build_labels_for_app_instance(
                app_instance, domain_names
            )
            ports = {f"{app_instance.docker_port}/tcp": None}
            container_id = self.docker_service.run_container(
                server=server,
                image=app_instance.docker_image,
                name=app_instance.internal_container_name,
                env=app_instance.env_vars,
                labels=labels,
                ports=ports,
                networks=["cp-net"],
            )
            logger.info("Deployed container %s for app instance %s", container_id, app_instance.id)
            app_instance.status = "running"
            db.commit()
            db.refresh(app_instance)
            return app_instance
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Deployment failed for app instance %s: %s", app_instance_id, exc)
            db.query(AppInstance).filter(AppInstance.id == app_instance_id).update(
                {"status": "error"}
            )
            db.commit()
            raise
        finally:
            db.close()

    def stop_app_instance(self, app_instance_id: int) -> None:
        db = self._get_db()
        try:
            app_instance = db.get(AppInstance, app_instance_id)
            if not app_instance:
                raise ValueError("AppInstance not found")
            server = db.get(Server, app_instance.server_id)
            if not server:
                raise ValueError("Server not found")
            self.docker_service.stop_container(server, app_instance.internal_container_name)
            app_instance.status = "stopped"
            db.commit()
        finally:
            db.close()

    def restart_app_instance(self, app_instance_id: int) -> AppInstance:
        db = self._get_db()
        try:
            app_instance = db.get(AppInstance, app_instance_id)
            if not app_instance:
                raise ValueError("AppInstance not found")
            server = db.get(Server, app_instance.server_id)
            if not server:
                raise ValueError("Server not found")
            self.docker_service.stop_container(server, app_instance.internal_container_name)
            self.docker_service.remove_container(server, app_instance.internal_container_name)
            ports = {f"{app_instance.docker_port}/tcp": None}
            labels = TraefikLabelBuilder.build_labels_for_app_instance(
                app_instance,
                self._domain_names(db, app_instance),
            )
            container_id = self.docker_service.run_container(
                server,
                app_instance.docker_image,
                app_instance.internal_container_name,
                app_instance.env_vars,
                labels,
                ports,
                networks=["cp-net"],
            )
            logger.info("Restarted container %s for app instance %s", container_id, app_instance.id)
            app_instance.status = "running"
            db.commit()
            db.refresh(app_instance)
            return app_instance
        finally:
            db.close()

    def _domain_names(self, db: Session, app_instance: AppInstance) -> List[str]:
        domains: List[str] = []
        if app_instance.main_domain_id:
            domain = db.get(Domain, app_instance.main_domain_id)
            if domain:
                domains.append(domain.domain_name)
        if app_instance.extra_domain_ids:
            extra_domains = (
                db.query(Domain)
                .filter(Domain.id.in_(app_instance.extra_domain_ids))
                .all()
            )
            domains.extend([d.domain_name for d in extra_domains])
        return domains

    def get_app_logs(self, app_instance_id: int, tail: int = 200) -> str:
        db = self._get_db()
        try:
            app_instance = db.get(AppInstance, app_instance_id)
            if not app_instance:
                raise ValueError("AppInstance not found")
            server = db.get(Server, app_instance.server_id)
            if not server:
                raise ValueError("Server not found")
            return self.docker_service.get_logs(
                server, app_instance.internal_container_name, tail=tail
            )
        finally:
            db.close()
