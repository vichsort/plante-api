from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.domain.exceptions import (
    PlantEError,
    UnauthorizedError,
    ForbiddenError,
    PlantNotFoundError,
    SubscriptionRequiredError,
    ExternalServiceError,
)
from src.api.response import ApiResponse


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ApiResponse.fail(code=code, message=message)
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _status_for(error: PlantEError) -> int:
    """Mapeia cada tipo de erro de domínio para o HTTP status correto."""
    mapping = {
        UnauthorizedError: 401,
        ForbiddenError: 403,
        PlantNotFoundError: 404,
        SubscriptionRequiredError: 403,
        ExternalServiceError: 502,
    }
    return mapping.get(type(error), 400)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers na instância do FastAPI."""

    @app.exception_handler(PlantEError)
    async def handle_domain_error(request: Request, exc: PlantEError) -> JSONResponse:
        return _error_response(
            status_code=_status_for(exc),
            code=exc.code,
            message=exc.message,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Erro interno. Tente novamente em instantes.",
        )