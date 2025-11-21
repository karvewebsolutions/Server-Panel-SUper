from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models import AppInstance, Application, Domain, Server
from .dns.dns_manager import DNSManager
from .docker_service import DockerService
from .subdomain_service import SubdomainService
from .traefik_service import TraefikLabelBuilder

logger = logging.getLogger(__name__)


class DomainContext(TypedDict):
    domain: Domain
    subdomains: Set[str]


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
            dns_success, dns_errors = self._provision_dns_records(
                dns_manager, app_instance, domain_map
            )
            if not dns_success:
                error_detail = "; ".join(dns_errors) if dns_errors else "unknown error"
                raise RuntimeError(
                    "DNS provisioning failed for one or more domains; aborting deployment"
                    f" ({error_detail})"
                )
            labels = TraefikLabelBuilder.build_labels_for_app_instance(
                app_instance, fqdn_list, wildcard_domains=wildcard_roots
            )
            data_dir = self._get_data_dir(app_instance.id)
            data_dir.mkdir(parents=True, exist_ok=True)

            ports = {f"{app_instance.docker_port}/tcp": None}
            container_id = self.docker_service.run_container(
                server=server,
                image=app_instance.docker_image,
                name=app_instance.internal_container_name,
                env=app_instance.env_vars,
                labels=labels,
                ports=ports,
                volumes=[f"{data_dir}:/data"],
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
            try:
                self.docker_service.stop_container(
                    server, app_instance.internal_container_name
                )
            except Exception as exc:  # pylint: disable=broad-except
                if self._is_container_missing_error(exc):
                    logger.info(
                        "Container %s already absent when stopping: %s",
                        app_instance.internal_container_name,
                        exc,
                    )
                else:
                    raise
            app_instance.status = "stopped"
            db.commit()
        finally:
            db.close()

    def restart_app_instance(
        self, app_instance_id: int, restore_dir: Optional[Path] = None
    ) -> AppInstance:
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

            data_dir = self._get_data_dir(app_instance.id)
            data_dir.parent.mkdir(parents=True, exist_ok=True)

            if restore_dir:
                self._validate_restore_dir(restore_dir)
                temp_restore_dir = data_dir.with_name(f"{data_dir.name}_temp_restore")
                try:
                    # First, copy the restore data to a temporary location. This is the step
                    # most likely to fail if the restore archive is corrupted or unreadable.
                    if temp_restore_dir.exists():
                        shutil.rmtree(temp_restore_dir)
                    shutil.copytree(restore_dir, temp_restore_dir)

                    # Only after the copy succeeds, stop the live container
                    self._stop_and_remove_container(
                        server, app_instance.internal_container_name
                    )

                    # Atomically replace the data directory with the restored content.
                    # The source `temp_restore_dir` is moved into place.
                    self._replace_data_dir(data_dir, temp_restore_dir)
                finally:
                    # Clean up the temporary directory if it still exists
                    if temp_restore_dir.exists():
                        shutil.rmtree(temp_restore_dir)
            else:
                # For a simple restart, just ensure the container is stopped and data dir exists
                self._stop_and_remove_container(server, app_instance.internal_container_name)
                data_dir.mkdir(parents=True, exist_ok=True)
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
                volumes=[f"{data_dir}:/data"],
                networks=["cp-net"],
            )
            logger.info("Restarted container %s for app instance %s", container_id, app_instance.id)
            app_instance.status = "running"
            db.commit()
            db.refresh(app_instance)
            return app_instance
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Restart failed for app instance %s: %s", app_instance_id, exc)
            # Use a transaction-safe update
            try:
                if not db.is_active:
                    db.begin()
                app_instance = db.get(AppInstance, app_instance_id)
                if app_instance:
                    app_instance.status = "error"
                    db.commit()
                else:
                    db.rollback()
            except Exception as db_exc:
                logger.error(
                    "Database error while setting error status for app instance %s: %s",
                    app_instance_id,
                    db_exc,
                )
                db.rollback()
            raise
        finally:
            db.close()

    def _get_data_dir(self, app_instance_id: int) -> Path:
        return Path("/var/lib/server-panel/app-data") / f"app_instance_{app_instance_id}"

    def _stop_and_remove_container(self, server: Server, container_name: str) -> None:
        """Ensure the container is stopped and removed before mutating mounted data."""
        try:
            self.docker_service.stop_container(server, container_name)
        except Exception as exc:  # pylint: disable=broad-except
            if self._is_container_missing_error(exc):
                logger.info(
                    "Container %s already absent when stopping: %s", container_name, exc
                )
            else:
                logger.warning(
                    "Error stopping container %s, proceeding with removal: %s",
                    container_name,
                    exc,
                )

        try:
            self.docker_service.remove_container(server, container_name)
        except Exception as exc:  # pylint: disable=broad-except
            if self._is_container_missing_error(exc):
                logger.info(
                    "Container %s already absent when removing: %s", container_name, exc
                )
            else:
                raise

    @staticmethod
    def _is_container_missing_error(exc: Exception) -> bool:
        """Return True if the exception indicates a missing container."""

        # Docker SDK specific error type check (local docker)
        try:
            import docker.errors  # type: ignore[import-untyped]

            if isinstance(exc, docker.errors.NotFound):
                return True
        except Exception:  # pylint: disable=broad-except
            # Ignore import errors or any unexpected issues so we can still
            # fall back to string checks below.
            pass

        def _iter_error_chain(error: Exception):
            current: Exception | None = error
            while current:
                yield current
                current = current.__cause__ or current.__context__

        def _collect_messages(error: Exception) -> List[str]:
            messages: List[str] = []
            seen: Set[str] = set()
            for err in _iter_error_chain(error):
                message = str(err).lower()
                if message and message not in seen:
                    seen.add(message)
                    messages.append(message)

                response = getattr(err, "response", None)
                if response is not None:
                    status_code = getattr(response, "status_code", None)
                    if status_code in {400, 404}:
                        try:
                            data = response.json()
                        except Exception:  # pylint: disable=broad-except
                            data = None

                        detail: Optional[str] = None
                        if isinstance(data, dict):
                            raw_detail = data.get("detail")
                            detail = raw_detail if isinstance(raw_detail, str) else None
                        elif isinstance(data, str):
                            detail = data

                        if detail:
                            detail_lower = detail.lower()
                            if detail_lower not in seen:
                                seen.add(detail_lower)
                                messages.append(detail_lower)
                            # If the agent responds with a wrapped Docker NotFound
                            # message we can return early when we see the expected
                            # keywords to avoid falling through to outer messages
                            # that lack the context.
                            if any(keyword in detail_lower for keyword in keywords):
                                return messages

                    try:
                        data = response.json()
                    except Exception:  # pylint: disable=broad-except
                        data = None

                    detail = data.get("detail") if isinstance(data, dict) else None
                    if detail:
                        detail_str = str(detail).lower()
                        if detail_str not in seen:
                            seen.add(detail_str)
                            messages.append(detail_str)
                    else:
                        try:
                            text = response.text
                        except Exception:  # pylint: disable=broad-except
                            text = None
                        if text:
                            text_lower = text.lower()
                            if text_lower not in seen:
                                seen.add(text_lower)
                                messages.append(text_lower)

            return messages

        keywords = ("not found", "no such container", "404", "missing container")
        messages = _collect_messages(exc)
        return any(keyword in message for message in messages for keyword in keywords)

    def _validate_restore_dir(self, restore_dir: Path) -> None:
        if not restore_dir.exists():
            raise ValueError(f"Restore directory not found: {restore_dir}")
        if not restore_dir.is_dir():
            raise ValueError(f"Restore path is not a directory: {restore_dir}")
        if not os.access(restore_dir, os.R_OK | os.X_OK):
            raise ValueError(f"Restore directory is not accessible: {restore_dir}")

    def _replace_data_dir(self, data_dir: Path, source_dir: Path) -> None:
        """Atomically replace the data directory with a new version from source_dir."""
        backup_dir = data_dir.with_name(f"{data_dir.name}_backup")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)

        # The source_dir (containing restored data) is expected to exist.
        # The live data_dir may or may not exist.
        backup_created = False
        if data_dir.exists():
            # Create a backup of the current data directory
            shutil.move(str(data_dir), str(backup_dir))
            backup_created = True

        try:
            # Move the new content into place
            shutil.move(str(source_dir), str(data_dir))
        except Exception:
            # If the move fails, restore the backup
            if backup_created:
                shutil.move(str(backup_dir), str(data_dir))
            raise
        finally:
            # Clean up the backup if the operation was successful
            if backup_dir.exists():
                shutil.rmtree(backup_dir)

    def _collect_domain_context(
        self, db: Session, app_instance: AppInstance
    ) -> tuple[List[str], Dict[int, DomainContext], List[str]]:
        fqdn_list: List[str] = []
        domain_map: Dict[int, DomainContext] = {}
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
                ctx["domain"].domain_name
                for ctx in domain_map.values()
                if ctx["domain"].is_wildcard and ctx["domain"].auto_ssl_enabled
            }
        )

        return fqdn_list, domain_map, wildcard_roots

    def _provision_dns_records(
        self,
        dns_manager: DNSManager,
        app_instance: AppInstance,
        domain_map: Dict[int, DomainContext],
    ) -> None:
        failures: List[str] = []
        for ctx in domain_map.values():
            domain: Domain = ctx["domain"]
            subdomains: Sequence[str] = (
                sorted(ctx["subdomains"])
                if ctx.get("subdomains")
                else []
            )
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
                failures.append(domain.domain_name)

        if failures:
            raise RuntimeError(
                "DNS provisioning failed for: " + ", ".join(sorted(failures))
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
