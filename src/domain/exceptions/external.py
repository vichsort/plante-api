from src.domain.exceptions.base import PlantEError


class ExternalServiceError(PlantEError):
    """Uma API externa (Gemini, Firebase, clima) falhou."""
    code = "PLANTE_5001_EXTERNAL_SERVICE_ERROR"
    status_code = 502

    def __init__(self, service: str, message: str = ""):
        super().__init__(
            message=f"External service '{service}' unavailable. {message}".strip(),
        )


class GeocodingError(PlantEError):
    """O serviço de geocodificação falhou."""
    code = "PLANTE_5002_GEOCODING_ERROR"
    status_code = 502

    def __init__(self, message: str = ""):
        super().__init__(
            message=f"Geocoding error. {message}".strip(),
        )
