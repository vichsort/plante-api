from uuid import UUID

from src.shared.domain import InvalidImageError, PlantEError


class LowConfidenceError(PlantEError):
    """A identificação retornou confiança abaixo do threshold aceitável."""
    code = "PLANTE_4400_LOW_CONFIDENCE"
    status_code = 422

    def __init__(self, confidence: float):
        super().__init__(
            message=f"Confidence too low on this image ({confidence:.0%}). Try one more clear image.",
        )


class IdentificationNotFoundError(PlantEError):
    """A identificação solicitada não existe ou não pertence ao usuário."""
    code = "PLANTE_4430_IDENTIFICATION_NOT_FOUND"
    status_code = 404

    def __init__(self, identification_id: UUID):
        super().__init__(
            message=f"Identification {identification_id} not found.",
        )


class NotAPlantError(InvalidImageError):
    """O provedor afirmou que a imagem não contém uma planta (mesmo código da API que `InvalidImageError`)."""

    def __init__(self, message: str = "The image does not contain a plant."):
        super().__init__(message=message)
