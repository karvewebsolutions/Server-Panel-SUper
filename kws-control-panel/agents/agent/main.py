from fastapi import FastAPI

from .services.docker import docker_client

app = FastAPI(title="KWS Agent")


@app.get("/")
def root():
    return {"message": "Agent service"}


@app.get("/health")
def health():
    info = docker_client.ping()
    return {"status": "ok", "docker": info}
