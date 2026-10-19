"""Exceções que qualquer módulo usa. As específicas moram em `domain/exceptions.py` de cada módulo."""
from uuid import UUID

from src.shared.domain.value_objects.json_value import JsonObject


class PlantEError(Exception):
    """
    Erro base do PlantE. Todos os erros de domínio herdam desta classe.
    """
    code: str = "PLANTE_4000_DOMAIN_ERROR"
    status_code: int = 400

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
        details: JsonObject | None = None,
    ) -> None:
        # Sem mensagem, a docstring da classe descreve o erro
        self.message = message or (type(self).__doc__ or self.code).strip()
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ExternalServiceError(PlantEError):
    """Uma API externa (Kindwise, PlantNet, Gemini, AWS) falhou."""
    code = "PLANTE_5001_EXTERNAL_SERVICE_ERROR"
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
    code = "PLANTE_4029_RATE_LIMIT_EXCEEDED"
    status_code = 429

    def __init__(self, limit: int, retry_after_seconds: int):
        super().__init__(
            message=f"Rate limit exceeded. Maximum of {limit} requests per minute allowed.",
            details={"limit": limit, "retry_after_seconds": retry_after_seconds},
        )


class UnauthorizedError(PlantEError):
    """Token inválido, expirado ou ausente."""
    code = "PLANTE_4006_UNAUTHORIZED"
    status_code = 401

    def __init__(self, message: str = "Authentication required."):
        super().__init__(message=message)


class UserNotFoundError(PlantEError):
    """Usuário não encontrado."""
    code = "PLANTE_4002_USER_NOT_FOUND"
    status_code = 404

    def __init__(self, message: str = "User not found.", user_id: UUID | None = None):
        if user_id:
            message = f"User {user_id} not found."
        super().__init__(message=message)


class InvalidImageError(PlantEError):
    """A imagem enviada é inválida ou não contém uma planta."""
    code = "PLANTE_4013_INVALID_IMAGE"
    status_code = 400

    def __init__(self, message: str = "Invalid image or unindentifiable plant."):
        super().__init__(message=message)
