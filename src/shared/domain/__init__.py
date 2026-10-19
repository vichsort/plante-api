"""Kernel compartilhado: tipos puros que qualquer módulo pode usar (sem framework nenhum)."""
from src.shared.domain.events import DomainEvent
from src.shared.domain.exceptions import (
    ExternalServiceError,
    InternalError,
    InvalidImageError,
    InvalidRequestError,
    PlantEError,
    RateLimitExceededError,
    ServiceUnavailableError,
    UnauthorizedError,
    UserNotFoundError,
)
from src.shared.domain.ports.access_token_verifier import IAccessTokenVerifier
from src.shared.domain.ports.domain_publisher import IDomainPublisher
from src.shared.domain.ports.image_sanitizer import IImageSanitizer
from src.shared.domain.ports.image_storage import IImageStorage
from src.shared.domain.ports.unit_of_work import IUnitOfWork
from src.shared.domain.value_objects.ids import UserId
from src.shared.domain.value_objects.json_value import JsonObject, JsonValue
from src.shared.domain.value_objects.local_calendar import LocalCalendar

__all__ = [
    "DomainEvent",
    "ExternalServiceError",
    "IAccessTokenVerifier",
    "IDomainPublisher",
    "IImageSanitizer",
    "IImageStorage",
    "IUnitOfWork",
    "InternalError",
    "InvalidImageError",
    "InvalidRequestError",
    "JsonObject",
    "JsonValue",
    "LocalCalendar",
    "PlantEError",
    "RateLimitExceededError",
    "ServiceUnavailableError",
    "UnauthorizedError",
    "UserId",
    "UserNotFoundError",
]
