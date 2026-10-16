"""Adapters técnicos comuns (banco, Redis, S3, imagens, resiliência, clientes de provedores). Sem regra de negócio."""
from src.shared.adapters.celery.publisher import (
    CeleryPublisher,
    EventRoute,
    TaskCall,
    TaskSender,
)
from src.shared.adapters.persistence.base import AuditMixin, Base, enum_values, utcnow
from src.shared.adapters.persistence.session import build_engine, build_session_factory
from src.shared.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.shared.adapters.pillow.image_sanitizer import PillowImageSanitizer
from src.shared.adapters.providers.errors import (
    provider_status_error,
    translate_provider_errors,
)
from src.shared.adapters.providers.gemini_client import SERVICE as GEMINI_SERVICE
from src.shared.adapters.providers.gemini_client import GeminiClient
from src.shared.adapters.providers.json_body import (
    parse_contract,
    parse_contract_json,
    parse_json_object,
)
from src.shared.adapters.redis.client import RedisClient
from src.shared.adapters.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    is_provider_failure,
)
from src.shared.adapters.s3.image_storage import S3ImageStorage

__all__ = [
    "GEMINI_SERVICE",
    "AuditMixin",
    "Base",
    "CeleryPublisher",
    "CircuitBreaker",
    "CircuitState",
    "EventRoute",
    "GeminiClient",
    "PillowImageSanitizer",
    "RedisClient",
    "S3ImageStorage",
    "SqlAlchemyUnitOfWork",
    "TaskCall",
    "TaskSender",
    "build_engine",
    "build_session_factory",
    "enum_values",
    "is_provider_failure",
    "parse_contract",
    "parse_contract_json",
    "parse_json_object",
    "provider_status_error",
    "translate_provider_errors",
    "utcnow",
]
