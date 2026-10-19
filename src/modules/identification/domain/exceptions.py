from uuid import UUID

from src.shared.domain import PlantEError


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


class NotAPlantError(PlantEError):
    """The provider stated the image holds no plant (the image itself is readable)."""
    code = "PLANTE_4401_NOT_A_PLANT"
    status_code = 422

    def __init__(self, message: str = "The image does not contain a plant."):
        super().__init__(message=message)
