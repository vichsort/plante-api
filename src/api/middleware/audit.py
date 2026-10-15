import time

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

log = structlog.get_logger()

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware de auditoria estruturada para todas as requisições HTTP da API.
    Mede tempo de resposta, identifica o controller/tags, status_code e registra via structlog.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Extrai o nome do controller baseado na tag do endpoint
            route = request.scope.get("route")
            controller_name = "UnknownController"
            if route and hasattr(route, "tags") and route.tags:
                controller_name = f"{route.tags[0].capitalize()}Controller"
            elif route and hasattr(route, "name") and route.name:
                controller_name = route.name

            log.info(
                "api.request_completed",
                controller=controller_name,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=request.client.host if request.client else None,
            )

            response.headers["X-Response-Time-Ms"] = str(duration_ms)
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log.error(
                "api.request_failed",
                method=request.method,
                path=request.url.path,
                error=str(exc),
                duration_ms=duration_ms,
                client_ip=request.client.host if request.client else None,
            )
            raise exc
