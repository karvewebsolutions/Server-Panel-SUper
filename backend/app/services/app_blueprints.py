from __future__ import annotations

from typing import Dict, List

BLUEPRINTS: Dict[str, dict] = {
    "wordpress": {
        "docker_image": "wordpress:latest",
        "docker_port": 80,
        "env": ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"],
        "requires": ["mysql"],
    },
    "nodejs": {
        "docker_image": "node:18-alpine",
        "docker_port": 3000,
        "env": ["NODE_ENV"],
        "requires": [],
    },
    "static": {
        "docker_image": "nginx:alpine",
        "docker_port": 80,
        "env": [],
        "requires": [],
    },
}


def get_app_blueprint(app_type: str) -> dict:
    return BLUEPRINTS.get(app_type, {})


def list_app_blueprints() -> List[dict]:
    return [dict({"type": key}, **value) for key, value in BLUEPRINTS.items()]
