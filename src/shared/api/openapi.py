from pydantic import BaseModel

from src.shared.api.response import ApiResponse
from src.shared.domain.exceptions import (
    InternalError,
    InvalidRequestError,
    PlantEError,
    RateLimitExceededError,
)
from src.shared.domain.value_objects.json_value import JsonObject, JsonValue

# Formato de `responses` do FastAPI: documentação por status, com o modelo e exemplos em JSON
ResponseDoc = dict[str, type[BaseModel] | JsonValue]
OpenApiResponses = dict[int | str, ResponseDoc]


def _envelope(code: str, message: str) -> JsonObject:
    return {
        "ok": False,
        "data": None,
        "error": {"code": code, "message": message, "details": None},
        "meta": {"timestamp": "2026-01-01T00:00:00+00:00"},
    }


def _message_for(error: type[PlantEError]) -> str:
    # Exceções com argumentos obrigatórios no __init__ usam a docstring como exemplo
    try:
        return error().message
    except TypeError:
        return (error.__doc__ or error.code).strip()


def _build(examples_by_status: dict[int, JsonObject]) -> OpenApiResponses:
    return {
        status: {
            "model": ApiResponse[None],
            "description": " | ".join(examples),
            "content": {"application/json": {"examples": examples}},
        }
        for status, examples in sorted(examples_by_status.items())
    }


def error_responses(*errors: type[PlantEError]) -> OpenApiResponses:
    """
    Gera a documentação OpenAPI dos erros de domínio que uma rota pode retornar,
    agrupando por status HTTP com um exemplo do envelope ApiResponse por código.
    """
    examples_by_status: dict[int, JsonObject] = {}
    for error in errors:
        examples_by_status.setdefault(error.status_code, {})[error.code] = {
            "summary": (error.__doc__ or error.code).strip(),
            "value": _envelope(error.code, _message_for(error)),
        }
    return _build(examples_by_status)


# Erros que qualquer rota pode retornar (validação, rate limit e falha inesperada)
COMMON_ERROR_RESPONSES: OpenApiResponses = error_responses(InvalidRequestError, RateLimitExceededError, InternalError)
