from collections.abc import Mapping

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, TypeAdapter
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.shared.api.response import ApiResponse
from src.shared.domain.exceptions import (
    InternalError,
    InvalidRequestError,
    MethodNotAllowedError,
    PlantEError,
    RouteNotFoundError,
)
from src.shared.domain.value_objects.json_value import JsonObject


class _ValidationIssue(BaseModel):
    """Um erro de validação do FastAPI, sem o valor recebido (que pode ter dado sensível)."""
    loc: list[str | int]
    msg: str
    type: str


_VALIDATION_ISSUES = TypeAdapter(list[_ValidationIssue])


def _error_response(error: PlantEError, headers: Mapping[str, str] | None = None) -> Response:
    body = ApiResponse.fail(code=error.code, message=error.message, details=error.details or None)
    return Response(
        content=body.model_dump_json(),
        status_code=error.status_code,
        headers=headers,
        media_type="application/json",
    )


def _from_framework(exc: StarletteHTTPException) -> PlantEError:
    """
    HTTP errors the framework raises by itself (no route, wrong method, unreadable body); the code
    raises none. Any other 4xx is an invalid request, and a 5xx is ours.
    """
    if exc.status_code == 404:
        return RouteNotFoundError()
    if exc.status_code == 405:
        return MethodNotAllowedError()
    if exc.status_code < 500:
        return InvalidRequestError(message=str(exc.detail))
    return InternalError()


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers na instância do FastAPI."""

    @app.exception_handler(PlantEError)
    async def handle_domain_error(request: Request, exc: PlantEError) -> Response:
        return _error_response(exc)

    @app.exception_handler(StarletteHTTPException)
    async def handle_framework_error(request: Request, exc: StarletteHTTPException) -> Response:
        # Keeps headers such as `Allow` on a 405
        return _error_response(_from_framework(exc), headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> Response:
        issues = _VALIDATION_ISSUES.validate_python(exc.errors())
        details: JsonObject = {"errors": [{"loc": list(i.loc), "msg": i.msg, "type": i.type} for i in issues]}
        return _error_response(InvalidRequestError(details=details))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> Response:
        return _error_response(InternalError())
