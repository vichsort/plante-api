"""Borda HTTP comum: envelope de resposta, tratamento de erros, documentação de erros e middlewares."""
from src.shared.api.exception_handlers import register_exception_handlers
from src.shared.api.middleware import (
    AuditMiddleware,
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from src.shared.api.middleware.rate_limit import WindowCounter
from src.shared.api.openapi import (
    COMMON_ERROR_RESPONSES,
    OpenApiResponses,
    error_responses,
)
from src.shared.api.response import ApiError, ApiMeta, ApiResponse

__all__ = [
    "COMMON_ERROR_RESPONSES",
    "ApiError",
    "ApiMeta",
    "ApiResponse",
    "AuditMiddleware",
    "CorrelationIdMiddleware",
    "OpenApiResponses",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "WindowCounter",
    "error_responses",
    "register_exception_handlers",
]
