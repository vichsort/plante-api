"""Exceções que qualquer módulo usa. As específicas moram em `domain/exceptions.py` de cada módulo."""
from typing import ClassVar
from uuid import UUID

from src.shared.domain.value_objects.json_value import JsonObject


class PlantEError(Exception):
    """
    Base of every PlantE error, never raised by itself. Each subclass sets `code`
    (`PLANTE_ABCD_NAME`: family, module, kind, sequence; see ARCHITECTURE.md §4) and `status_code`,
    and the HTTP handler turns it into the envelope.
    """
    code: ClassVar[str]
    status_code: ClassVar[int]

    def __init__(self, message: str | None = None, details: JsonObject | None = None) -> None:
        if not hasattr(type(self), "code"):
            # A bug, not a client error: the generic handler answers 500
            raise TypeError(f"{type(self).__name__} has no error code; raise a subclass of it")
        # Sem mensagem, a docstring da classe descreve o erro
        self.message = message or (type(self).__doc__ or self.code).strip()
        self.details = details or {}
        super().__init__(self.message)


class InvalidRequestError(PlantEError):
    """The request body, query or path failed validation."""
    code = "PLANTE_4000_VALIDATION_ERROR"
    status_code = 422

    def __init__(self, message: str = "Invalid request data.", details: JsonObject | None = None):
        super().__init__(message=message, details=details)


class InternalError(PlantEError):
    """Unexpected failure; the details only go to the log."""
    code = "PLANTE_5000_INTERNAL_ERROR"
    status_code = 500

    def __init__(self, message: str = "Internal error. Please try again shortly."):
        super().__init__(message=message)


class ServiceUnavailableError(PlantEError):
    """A dependency of our own infrastructure (database, Redis) is not responding."""
    code = "PLANTE_5030_SERVICE_UNAVAILABLE"
    status_code = 503

    def __init__(self, message: str = "Service temporarily unavailable.", details: JsonObject | None = None):
        super().__init__(message=message, details=details)


class ExternalServiceError(PlantEError):
    """Uma API externa (Kindwise, PlantNet, Gemini, AWS) falhou."""
    code = "PLANTE_5010_EXTERNAL_SERVICE_ERROR"
    status_code = 502

    def __init__(
        self,
        message: str = "External service unavailable.",
        service: str = "External",
        retryable: bool = False,
    ):
        super().__init__(
            message=f"External service '{service}' unavailable. {message}".strip() if service else message,
        )
        # Falha transitória de infraestrutura (rede, timeout, 5xx, 429): conta para o circuit breaker
        self.retryable = retryable


class RateLimitExceededError(PlantEError):
    """Cliente excedeu o limite de requisições da janela atual."""
    code = "PLANTE_4050_RATE_LIMIT_EXCEEDED"
    status_code = 429

    def __init__(self, limit: int, retry_after_seconds: int):
        super().__init__(
            message=f"Rate limit exceeded. Maximum of {limit} requests per minute allowed.",
            details={"limit": limit, "retry_after_seconds": retry_after_seconds},
        )


class UnauthorizedError(PlantEError):
    """Token inválido, expirado ou ausente."""
    code = "PLANTE_4010_UNAUTHORIZED"
    status_code = 401

    def __init__(self, message: str = "Authentication required."):
        super().__init__(message=message)


class UserNotFoundError(PlantEError):
    """Usuário não encontrado."""
    code = "PLANTE_4031_USER_NOT_FOUND"
    status_code = 404

    def __init__(self, message: str = "User not found.", user_id: UUID | None = None):
        if user_id:
            message = f"User {user_id} not found."
        super().__init__(message=message)


class InvalidImageError(PlantEError):
    """A imagem enviada é inválida ou não contém uma planta."""
    code = "PLANTE_4001_INVALID_IMAGE"
    status_code = 400

    def __init__(self, message: str = "Invalid image or unindentifiable plant."):
        super().__init__(message=message)
