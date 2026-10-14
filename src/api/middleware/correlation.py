import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

_HEADER_NAME = "X-Correlation-ID"

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware responsável por atribuir ou propagar um UUID de rastreamento (Correlation ID)
    em cada requisição HTTP e injetar no contexto do structlog para tracing distribuído.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(_HEADER_NAME) or str(uuid.uuid4())
        
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        response: Response = await call_next(request)
        response.headers[_HEADER_NAME] = correlation_id
        return response
