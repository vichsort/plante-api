from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.response import ApiResponse
from src.domain.exceptions import PlantEError


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    body = ApiResponse.fail(code=code, message=message, details=details)
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers na instância do FastAPI."""

    @app.exception_handler(PlantEError)
    async def handle_domain_error(request: Request, exc: PlantEError) -> JSONResponse:
        return _error_response(
            status_code=getattr(exc, "status_code", 400),
            code=exc.code,
            message=exc.message,
            details=getattr(exc, "details", None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        body = ApiResponse.fail(
            code="PLANTE_4220_VALIDATION_ERROR",
            message="Dados da requisição inválidos.",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(
            status_code=500,
            code="PLANTE_5000_INTERNAL_ERROR",
            message="Erro interno. Tente novamente em instantes.",
        )