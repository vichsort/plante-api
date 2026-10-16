from uuid import UUID

from src.shared.domain import InvalidImageError, PlantEError


class PlantIdentificationError(PlantEError):
    """A IA não conseguiu identificar a planta com confiança suficiente."""
    code = "PLANTE_4010_IDENTIFICATION_FAILED"
    status_code = 422

    def __init__(self, message: str = "Could not identify any plant in this image."):
        super().__init__(message=message)


class LowConfidenceError(PlantEError):
    """A identificação retornou confiança abaixo do threshold aceitável."""
    code = "PLANTE_4011_LOW_CONFIDENCE"
    status_code = 422

    def __init__(self, confidence: float):
        super().__init__(
            message=f"Confidence too low on this image ({confidence:.0%}). Try one more clear image.",
        )


class IdentificationNotFoundError(PlantEError):
    """A identificação solicitada não existe ou não pertence ao usuário."""
    code = "PLANTE_4012_IDENTIFICATION_NOT_FOUND"
    status_code = 404

    def __init__(self, identification_id: UUID):
        super().__init__(
            message=f"Identification {identification_id} not found.",
        )


class NotAPlantError(InvalidImageError):
    """O provedor afirmou que a imagem não contém uma planta (mesmo código da API que `InvalidImageError`)."""

    def __init__(self, message: str = "The image does not contain a plant."):
        super().__init__(message=message)


class SpeciesNotFoundError(PlantEError):
    """A espécie solicitada não existe."""
    code = "PLANTE_4014_SPECIES_NOT_FOUND"
    status_code = 404

    def __init__(self, species: UUID | str):  # ID ou nome científico
        super().__init__(
            message=f"Species {species} not found.",
        )
