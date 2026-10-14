from src.domain.exceptions.base import PlantEError


class RateLimitExceededError(PlantEError):
    """Cliente excedeu o limite de requisições da janela atual."""
    code = "PLANTE_4029_RATE_LIMIT_EXCEEDED"
    status_code = 429

    def __init__(self, limit: int, retry_after_seconds: int):
        super().__init__(
            message=f"Rate limit exceeded. Maximum of {limit} requests per minute allowed.",
            details={"limit": limit, "retry_after_seconds": retry_after_seconds},
        )
