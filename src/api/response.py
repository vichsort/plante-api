from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """Envelope padrão de todas as respostas da API."""
    success: bool
    data: T | None = None
    error: "ApiError | None" = None

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, code: str, message: str) -> "ApiResponse[None]":
        return cls(success=False, error=ApiError(code=code, message=message))

class ApiError(BaseModel):
    code: str
    message: str