from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

class ApiMeta(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None

class ApiResponse(BaseModel, Generic[T]):
    """Envelope padrão de todas as respostas da API."""
    ok: bool = True
    data: T | None = None
    error: ApiError | None = None
    meta: ApiMeta = Field(default_factory=ApiMeta)

    @classmethod
    def success(cls, data: T, meta: ApiMeta | None = None) -> "ApiResponse[T]":
        return cls(ok=True, data=data, meta=meta or ApiMeta())

    @classmethod
    def fail(cls, code: str, message: str, details: dict[str, Any] | None = None) -> "ApiResponse[None]":
        return cls(
            ok=False,
            data=None,
            error=ApiError(code=code, message=message, details=details),
            meta=ApiMeta(),
        )