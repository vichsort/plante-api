"""
Leitura das respostas JSON dos provedores de IA.

O corpo vira `JsonObject` e é validado contra o modelo Pydantic do contrato do provedor (só os
campos usados; o resto é descartado e nunca é guardado). Resposta fora do contrato é falha do provedor, não do usuário:
`ExternalServiceError` não retryable, com log para investigar a mudança de formato.
"""
import structlog
from pydantic import BaseModel, TypeAdapter, ValidationError

from src.shared.domain.exceptions import ExternalServiceError
from src.shared.domain.value_objects.json_value import JsonObject

log = structlog.stdlib.get_logger()

_JSON_OBJECT: TypeAdapter[JsonObject] = TypeAdapter(JsonObject)


def parse_json_object(body: bytes | str, service: str) -> JsonObject:
    try:
        return _JSON_OBJECT.validate_json(body)
    except ValidationError as exc:
        raise ExternalServiceError(message="Invalid JSON response.", service=service) from exc


def parse_contract[M: BaseModel](model: type[M], data: JsonObject, service: str) -> M:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        log.error(
            "provider.unexpected_response",
            service=service,
            model=model.__name__,
            error_count=exc.error_count(),
            errors=str(exc)[:1000],
        )
        raise ExternalServiceError(message="Unexpected response format.", service=service) from exc


def parse_contract_json[M: BaseModel](model: type[M], body: bytes | str, service: str) -> M:
    """Como `parse_contract`, direto do corpo em texto."""
    return parse_contract(model, parse_json_object(body, service), service)
