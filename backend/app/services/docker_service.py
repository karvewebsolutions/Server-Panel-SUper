from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests  # type: ignore[import-untyped]

from ..models.app_models import Server

logger = logging.getLogger(__name__)


class DockerService:
    def _get_local_client(self):
        import docker

        return docker.from_env()

    def _agent_headers(self, server: Server) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if server.agent_token:
            headers["X-Agent-Token"] = server.agent_token
        return headers

    def _agent_request(
        self,
        server: Server,
        path: str,
        payload: dict | None = None,
        method: str = "post",
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        if not server.agent_url:
            raise ValueError("Agent URL not configured for remote server")
        url = f"{server.agent_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = requests.request(
                method,
                url,
                json=payload or {},
                params=params or {},
                headers=self._agent_headers(server),
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as exc:  # type: ignore[import-untyped]
            logger.error("Failed to contact agent %s: %s", server.name, exc)
            raise RuntimeError(f"Agent request failed: {exc}") from exc
        return response.json() if response.content else None

    def run_container(
        self,
        server: Server,
        image: str,
        name: str,
        env: Dict[str, Any],
        labels: Dict[str, str],
        ports: Dict[str, Optional[int]],
        volumes: Optional[List[str]] = None,
        networks: Optional[List[str]] = None,
    ) -> str:
        networks = networks or []
        volumes = volumes or []
        logger.info("Starting container %s on server %s", name, server.name)
        if not server.is_master or server.agent_url:
            payload = {
                "image": image,
                "name": name,
                "env": env,
                "labels": labels,
                "ports": ports,
                "volumes": volumes,
                "networks": networks,
            }
            data = self._agent_request(server, "/docker/run", payload)
            container_id = data.get("id") if isinstance(data, dict) else None
            if not container_id:
                raise RuntimeError("Agent did not return container id")
            return container_id

        client = self._get_local_client()
        container = client.containers.run(
            image,
            name=name,
            environment=env,
            labels=labels,
            ports=ports,
            volumes=volumes or None,
            detach=True,
            network=networks[0] if networks else None,
        )
        if networks and len(networks) > 1:
            for net_name in networks[1:]:
                try:
                    network = client.networks.get(net_name)
                    network.connect(container)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("Failed to connect container to network %s: %s", net_name, exc)
        return container.id

    def stop_container(self, server: Server, container_name_or_id: str) -> None:
        logger.info("Stopping container %s on server %s", container_name_or_id, server.name)
        if not server.is_master or server.agent_url:
            self._agent_request(server, "/docker/stop", {"container": container_name_or_id})
            return
        client = self._get_local_client()
        try:
            container = client.containers.get(container_name_or_id)
            container.stop()
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Error stopping container %s: %s", container_name_or_id, exc)
            raise

    def remove_container(self, server: Server, container_name_or_id: str) -> None:
        logger.info("Removing container %s on server %s", container_name_or_id, server.name)
        if not server.is_master or server.agent_url:
            self._agent_request(server, "/docker/remove", {"container": container_name_or_id})
            return
        client = self._get_local_client()
        try:
            container = client.containers.get(container_name_or_id)
            container.remove(force=True)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Error removing container %s: %s", container_name_or_id, exc)
            raise

    def get_logs(self, server: Server, container_name_or_id: str, tail: int = 200) -> str:
        logger.info("Fetching logs for %s on server %s", container_name_or_id, server.name)
        if not server.is_master or server.agent_url:
            data = self._agent_request(
                server,
                "/docker/logs",
                method="get",
                params={"container": container_name_or_id, "tail": tail},
            )
            return data.get("logs", "") if isinstance(data, dict) else ""
        client = self._get_local_client()
        try:
            container = client.containers.get(container_name_or_id)
            return container.logs(tail=tail).decode("utf-8")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Error fetching logs for container %s: %s", container_name_or_id, exc)
            raise

    def list_containers(self, server: Server, filters: Optional[Dict[str, Any]] = None) -> list:
        logger.info("Listing containers on server %s", server.name)
        filters = filters or {}
        if not server.is_master or server.agent_url:
            data = self._agent_request(server, "/docker/containers", {"filters": filters})
            return data if isinstance(data, list) else []
        client = self._get_local_client()
        containers = client.containers.list(filters=filters)
        return [c.attrs for c in containers]
