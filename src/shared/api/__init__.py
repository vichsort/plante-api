"""Borda HTTP comum: envelope de resposta, tratamento de erros, documentação de erros e middlewares."""
from src.shared.api.authentication import CurrentUserId, install_authentication
from src.shared.api.exception_handlers import register_exception_handlers
from src.shared.api.images import install_image_links
from src.shared.api.images import router as images_router
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
from src.shared.api.response import (
    ApiError,
    ApiMeta,
    ApiResponse,
    MessageResponse,
)

__all__ = [
    "COMMON_ERROR_RESPONSES",
    "ApiError",
    "ApiMeta",
    "ApiResponse",
    "AuditMiddleware",
    "CorrelationIdMiddleware",
    "CurrentUserId",
    "MessageResponse",
    "OpenApiResponses",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "WindowCounter",
    "error_responses",
    "images_router",
    "install_authentication",
    "install_image_links",
    "register_exception_handlers",
]
