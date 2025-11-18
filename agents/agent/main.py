from __future__ import annotations

import os
import platform
import socket
from typing import Dict, List, Optional

import docker
import psutil  # type: ignore
from fastapi import Depends, FastAPI, HTTPException, Request

AGENT_TOKEN = os.getenv("AGENT_TOKEN", "")
SERVER_NAME = os.getenv("SERVER_NAME", platform.node())

app = FastAPI(title="KWS Agent", version="0.1.0")


def require_token(request: Request):
    if request.method in {"POST", "PUT", "DELETE"}:
        header = request.headers.get("X-Agent-Token")
        if AGENT_TOKEN and header != AGENT_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")


def _get_docker_client() -> docker.DockerClient:
    return docker.from_env()


def _get_ip_addresses() -> List[str]:
    addresses: List[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None):
            addr = info[4][0]
            if addr not in addresses:
                addresses.append(addr)
    except Exception:
        pass
    return addresses


def _docker_info() -> Dict[str, int]:
    running = total = 0
    try:
        client = _get_docker_client()
        containers = client.containers.list(all=True)
        total = len(containers)
        running = len([c for c in containers if c.status == "running"])
    except Exception:
        running = total = 0
    return {
        "docker_running_containers": running,
        "docker_total_containers": total,
    }


@app.middleware("http")
async def token_middleware(request: Request, call_next):
    require_token(request)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok", "name": SERVER_NAME}


@app.get("/info")
def info():
    docker_ok = True
    try:
        _get_docker_client().ping()
    except Exception:
        docker_ok = False
    return {
        "hostname": platform.node(),
        "os": platform.platform(),
        "ip_addresses": _get_ip_addresses(),
        "docker_available": docker_ok,
    }


@app.get("/metrics")
def metrics():
    disk = psutil.disk_usage("/")
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    docker_stats = _docker_info()
    return {
        "cpu_percent": cpu,
        "memory_percent": mem.percent,
        "disk_percent": disk.percent,
        **docker_stats,
    }


@app.post("/docker/run")
def docker_run(payload: Dict[str, Optional[object]], request: Request = Depends(require_token)):
    client = _get_docker_client()
    image = str(payload.get("image"))
    name = payload.get("name") or None
    env = payload.get("env") or {}
    labels = payload.get("labels") or {}
    ports = payload.get("ports") or {}
    volumes = payload.get("volumes") or None
    networks = payload.get("networks") or []
    try:
        client.images.pull(image)
    except Exception:
        pass
    try:
        container = client.containers.run(
            image,
            name=name,
            environment=env,
            labels=labels,
            ports=ports,
            volumes=volumes,
            detach=True,
        )
        for net in networks:
            try:
                network = client.networks.get(net)
                network.connect(container)
            except Exception:
                continue
    except docker.errors.DockerException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": container.id}


@app.post("/docker/stop")
def docker_stop(payload: Dict[str, str], request: Request = Depends(require_token)):
    container_ref = payload.get("container")
    if not container_ref:
        raise HTTPException(status_code=400, detail="container required")
    client = _get_docker_client()
    try:
        container = client.containers.get(container_ref)
        container.stop()
    except docker.errors.DockerException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "stopped"}


@app.post("/docker/remove")
def docker_remove(payload: Dict[str, str], request: Request = Depends(require_token)):
    container_ref = payload.get("container")
    if not container_ref:
        raise HTTPException(status_code=400, detail="container required")
    client = _get_docker_client()
    try:
        container = client.containers.get(container_ref)
        container.remove(force=True)
    except docker.errors.DockerException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "removed"}


@app.get("/docker/logs")
def docker_logs(container: str, tail: int = 200):
    client = _get_docker_client()
    try:
        container_obj = client.containers.get(container)
        logs = container_obj.logs(tail=tail).decode("utf-8")
    except docker.errors.DockerException as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"logs": logs}
