"""Kernel compartilhado: tipos puros que qualquer módulo pode usar (sem framework nenhum)."""
from src.shared.domain.events import DomainEvent
from src.shared.domain.exceptions import (
    ExternalServiceError,
    InvalidImageError,
    PlantEError,
    RateLimitExceededError,
)
from src.shared.domain.ports.domain_publisher import IDomainPublisher
from src.shared.domain.ports.image_sanitizer import IImageSanitizer
from src.shared.domain.ports.image_storage import IImageStorage
from src.shared.domain.value_objects.ids import UserId
from src.shared.domain.value_objects.json_value import JsonObject, JsonValue

__all__ = [
    "DomainEvent",
    "ExternalServiceError",
    "IDomainPublisher",
    "IImageSanitizer",
    "IImageStorage",
    "InvalidImageError",
    "JsonObject",
    "JsonValue",
    "PlantEError",
    "RateLimitExceededError",
    "UserId",
]
