import re
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

_HEADER_NAME = "X-Correlation-ID"
_VALID_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware responsável por atribuir ou propagar um Correlation ID em cada requisição HTTP
    e injetá-lo no contexto do structlog, permitindo correlacionar os logs de uma mesma requisição.

    O cabeçalho recebido só é aceito se respeitar `^[A-Za-z0-9._-]{1,128}$` (sem exigir formato
    UUID, para compatibilidade com IDs de gateways); caso contrário, um novo UUID4 é gerado.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get(_HEADER_NAME)
        if incoming and _VALID_CORRELATION_ID.fullmatch(incoming):
            correlation_id = incoming
        else:
            correlation_id = str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        response: Response = await call_next(request)
        response.headers[_HEADER_NAME] = correlation_id
        return response
