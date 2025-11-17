from __future__ import annotations

from typing import Any, Dict, List


class TraefikLabelBuilder:
    @staticmethod
    def build_labels_for_app_instance(app_instance: Any, domains: List[str]) -> Dict[str, str]:
        router_name = f"cp-{app_instance.id}-router"
        service_name = f"cp-{app_instance.id}-service"
        effective_domains = domains or [app_instance.internal_container_name]
        host_rules = " || ".join([f"Host(`{domain}`)" for domain in effective_domains])
        labels: Dict[str, str] = {
            "traefik.enable": "true",
            f"traefik.http.routers.{router_name}.rule": host_rules,
            f"traefik.http.routers.{router_name}.entrypoints": "websecure",
            f"traefik.http.routers.{router_name}.tls.certresolver": "le",
            f"traefik.http.services.{service_name}.loadbalancer.server.port": str(
                app_instance.docker_port
            ),
        }
        return labels
