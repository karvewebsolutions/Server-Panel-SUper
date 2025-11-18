from .alerts import router as alerts_router
from .apps import router as apps_router
from .backups import router as backups_router
from .dns import router as dns_router
from .domains import router as domains_router
from .logs import router as logs_router
from .servers import router as servers_router

__all__ = [
    "alerts_router",
    "apps_router",
    "dns_router",
    "domains_router",
    "logs_router",
    "servers_router",
]
