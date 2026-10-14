from typing import Any

from src.api.response import ApiResponse
from src.domain.exceptions import PlantEError, RateLimitExceededError

OpenApiResponses = dict[int | str, dict[str, Any]]


def _envelope(code: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "data": None,
        "error": {"code": code, "message": message, "details": None},
        "meta": {"timestamp": "2026-01-01T00:00:00+00:00"},
    }


def _message_for(error: type[PlantEError]) -> str:
    # Exceções com argumentos obrigatórios no __init__ usam a docstring como exemplo
    try:
        return error().message  # type: ignore[call-arg]
    except TypeError:
        return (error.__doc__ or error.code).strip()


def _build(examples_by_status: dict[int, dict[str, Any]]) -> OpenApiResponses:
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
    examples_by_status: dict[int, dict[str, Any]] = {}
    for error in errors:
        examples_by_status.setdefault(error.status_code, {})[error.code] = {
            "summary": (error.__doc__ or error.code).strip(),
            "value": _envelope(error.code, _message_for(error)),
        }
    return _build(examples_by_status)


# Erros que qualquer rota pode retornar (validação, rate limit e falha inesperada)
COMMON_ERROR_RESPONSES: OpenApiResponses = {
    **_build({
        422: {
            "PLANTE_4220_VALIDATION_ERROR": {
                "summary": "Dados da requisição inválidos.",
                "value": _envelope("PLANTE_4220_VALIDATION_ERROR", "Dados da requisição inválidos."),
            },
        },
        500: {
            "PLANTE_5000_INTERNAL_ERROR": {
                "summary": "Erro interno inesperado.",
                "value": _envelope("PLANTE_5000_INTERNAL_ERROR", "Erro interno. Tente novamente em instantes."),
            },
        },
    }),
    **error_responses(RateLimitExceededError),
}
