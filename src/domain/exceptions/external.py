from src.domain.exceptions.base import PlantEError


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

