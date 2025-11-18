from __future__ import annotations

import logging
from typing import Dict, List, Sequence

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models import AppInstance, Application, Domain, Server
from .dns.dns_manager import DNSManager
from .docker_service import DockerService
from .subdomain_service import SubdomainService
from .traefik_service import TraefikLabelBuilder

logger = logging.getLogger(__name__)


class DeploymentEngine:
    def __init__(self, db_factory=SessionLocal):
        self.db_factory = db_factory
        self.docker_service = DockerService()
        self.subdomain_service = SubdomainService()

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

            fqdn_list, domain_map, wildcard_roots = self._collect_domain_context(db, app_instance)
            dns_manager = DNSManager(db)
            self._provision_dns_records(dns_manager, app_instance, domain_map)
            labels = TraefikLabelBuilder.build_labels_for_app_instance(
                app_instance, fqdn_list, wildcard_domains=wildcard_roots
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
            fqdn_list, domain_map, wildcard_roots = self._collect_domain_context(db, app_instance)
            dns_manager = DNSManager(db)
            self._provision_dns_records(dns_manager, app_instance, domain_map)
            self.docker_service.stop_container(server, app_instance.internal_container_name)
            self.docker_service.remove_container(server, app_instance.internal_container_name)
            ports = {f"{app_instance.docker_port}/tcp": None}
            labels = TraefikLabelBuilder.build_labels_for_app_instance(
                app_instance,
                fqdn_list,
                wildcard_domains=wildcard_roots,
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

    def _collect_domain_context(
        self, db: Session, app_instance: AppInstance
    ) -> tuple[List[str], Dict[int, Dict[str, object]], List[str]]:
        fqdn_list: List[str] = []
        domain_map: Dict[int, Dict[str, object]] = {}
        mappings = sorted(
            list(app_instance.domain_mappings),
            key=lambda m: (not m.is_primary, m.id),
        )
        for mapping in mappings:
            domain = mapping.domain or db.get(Domain, mapping.domain_id)
            if not domain:
                continue
            clean_sub = (mapping.subdomain or "").strip().lower().strip(".")
            fqdn = SubdomainService.build_fqdn(clean_sub, domain.domain_name)
            fqdn_list.append(fqdn)
            bucket = domain_map.setdefault(
                domain.id, {"domain": domain, "subdomains": set()}
            )
            if clean_sub and not domain.is_wildcard:
                bucket["subdomains"].add(clean_sub)

        if not fqdn_list and app_instance.main_domain_id:
            domain = db.get(Domain, app_instance.main_domain_id)
            if domain:
                fqdn_list.append(domain.domain_name)
                domain_map.setdefault(domain.id, {"domain": domain, "subdomains": set()})

        wildcard_roots = sorted(
            {
                ctx["domain"].domain_name  # type: ignore[index]
                for ctx in domain_map.values()
                if ctx["domain"].is_wildcard and ctx["domain"].auto_ssl_enabled  # type: ignore[index]
            }
        )

        return fqdn_list, domain_map, wildcard_roots

    def _provision_dns_records(
        self,
        dns_manager: DNSManager,
        app_instance: AppInstance,
        domain_map: Dict[int, Dict[str, object]],
    ) -> None:
        for ctx in domain_map.values():
            domain: Domain = ctx["domain"]  # type: ignore[assignment]
            subdomains: Sequence[str] = sorted(ctx["subdomains"]) if ctx.get("subdomains") else []
            try:
                dns_manager.create_dns_for_deployment(
                    app_instance,
                    domain,
                    subdomains=list(subdomains),
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.error(
                    "DNS provisioning failed for domain %s: %s", domain.domain_name, exc
                )

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
