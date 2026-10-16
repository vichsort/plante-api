from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, TypeAdapter

from src.shared.api.response import ApiResponse
from src.shared.domain.exceptions import PlantEError
from src.shared.domain.value_objects.json_value import JsonObject


class _ValidationIssue(BaseModel):
    """Um erro de validação do FastAPI, sem o valor recebido (que pode ter dado sensível)."""
    loc: list[str | int]
    msg: str
    type: str


_VALIDATION_ISSUES = TypeAdapter(list[_ValidationIssue])


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: JsonObject | None = None,
) -> Response:
    body = ApiResponse.fail(code=code, message=message, details=details)
    return Response(content=body.model_dump_json(), status_code=status_code, media_type="application/json")


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers na instância do FastAPI."""

    @app.exception_handler(PlantEError)
    async def handle_domain_error(request: Request, exc: PlantEError) -> Response:
        return _error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> Response:
        issues = _VALIDATION_ISSUES.validate_python(exc.errors())
        return _error_response(
            status_code=422,
            code="PLANTE_4220_VALIDATION_ERROR",
            message="Dados da requisição inválidos.",
            details={"errors": [{"loc": list(i.loc), "msg": i.msg, "type": i.type} for i in issues]},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> Response:
        return _error_response(
            status_code=500,
            code="PLANTE_5000_INTERNAL_ERROR",
            message="Erro interno. Tente novamente em instantes.",
        )
