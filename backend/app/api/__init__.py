from fastapi import APIRouter

from .routes import auth, health
from .v1 import apps as apps_v1
from .v1 import dns as dns_v1
from .v1 import domains as domains_v1
from .v1 import servers as servers_v1

api_router = APIRouter()
api_router.include_router(health.router, prefix="/api")
api_router.include_router(auth.router, prefix="/api")
api_router.include_router(dns_v1.router, prefix="/api/v1")
api_router.include_router(domains_v1.router, prefix="/api/v1")
api_router.include_router(apps_v1.router, prefix="/api/v1")
api_router.include_router(servers_v1.router, prefix="/api/v1")

__all__ = ["api_router"]
