from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import structlog

from src.domain.exceptions import ExternalServiceError, InvalidImageError

log = structlog.get_logger()

_INVALID_IMAGE_STATUSES = frozenset({400})
_MISCONFIGURED_STATUSES = frozenset({401, 403})


def provider_status_error(service: str, status: int) -> ExternalServiceError:
    """
    ExternalServiceError para uma resposta HTTP de erro do provedor.
    5xx e 429 são transitórios (retryable); 401/403 indicam chave inválida e são logados como erro.
    """
    if status in _MISCONFIGURED_STATUSES:
        log.error("provider.misconfigured", service=service, status=status)
    return ExternalServiceError(
        message=f"Provider returned HTTP {status}.",
        service=service,
        retryable=status >= 500 or status == 429,
    )


@asynccontextmanager
async def translate_provider_errors(
    service: str,
    invalid_image_statuses: frozenset[int] = _INVALID_IMAGE_STATUSES,
) -> AsyncIterator[None]:
    """
    Traduz exceções httpx de um provedor de IA para erros de domínio.
    Status em `invalid_image_statuses` → InvalidImageError; falhas de infraestrutura
    (rede, timeout, 5xx, 429) → ExternalServiceError(retryable=True); demais → ExternalServiceError.
    """
    try:
        yield
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in invalid_image_statuses:
            raise InvalidImageError() from exc
        raise provider_status_error(service, status) from exc
    except httpx.TransportError as exc:
        raise ExternalServiceError(
            message=f"{type(exc).__name__}.",
            service=service,
            retryable=True,
        ) from exc
    except httpx.HTTPError as exc:
        raise ExternalServiceError(message=f"{type(exc).__name__}.", service=service) from exc
