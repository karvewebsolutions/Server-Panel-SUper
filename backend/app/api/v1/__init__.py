from .apps import router as apps_router
from .dns import router as dns_router
from .domains import router as domains_router
from .servers import router as servers_router

__all__ = ["apps_router", "dns_router", "domains_router", "servers_router"]
