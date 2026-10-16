from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.shared.domain.value_objects.json_value import JsonObject


class ApiMeta(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class ApiError(BaseModel):
    code: str
    message: str
    details: JsonObject | None = None

# `data` das rotas que só confirmam a ação (comentário, não docstring: ela iria para o OpenAPI)
class MessageResponse(BaseModel):
    message: str

class ApiResponse[T](BaseModel):
    """Envelope padrão de todas as respostas da API."""
    ok: bool = True
    data: T | None = None
    error: ApiError | None = None
    meta: ApiMeta = Field(default_factory=ApiMeta)

    @classmethod
    def success(cls, data: T, meta: ApiMeta | None = None) -> "ApiResponse[T]":
        return cls(ok=True, data=data, meta=meta or ApiMeta())

    @staticmethod
    def fail(code: str, message: str, details: JsonObject | None = None) -> "ApiResponse[None]":
        return ApiResponse[None](
            ok=False,
            data=None,
            error=ApiError(code=code, message=message, details=details),
            meta=ApiMeta(),
        )
