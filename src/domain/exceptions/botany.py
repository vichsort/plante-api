from typing import Any

from src.domain.exceptions.base import PlantEError


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

    def __init__(self, identification_id: Any):
        super().__init__(
            message=f"Identification {identification_id} not found.",
        )


class InvalidImageError(PlantEError):
    """A imagem enviada é inválida ou não contém uma planta."""
    code = "PLANTE_4013_INVALID_IMAGE"
    status_code = 400

    def __init__(self, message: str = "Invalid image or unindentifiable plant."):
        super().__init__(message=message)


class SpeciesNotFoundError(PlantEError):
    """A espécie solicitada não existe."""
    code = "PLANTE_4014_SPECIES_NOT_FOUND"
    status_code = 404

    def __init__(self, species_id: Any):
        super().__init__(
            message=f"Species {species_id} not found.",
        )


class SampleNotFoundError(PlantEError):
    """A amostra solicitada não existe."""
    code = "PLANTE_4015_SAMPLE_NOT_FOUND"
    status_code = 404

    def __init__(self, sample_id: Any):
        super().__init__(
            message=f"Sample {sample_id} not found.",
        )
