from uuid import UUID

from src.shared.domain import PlantEError


class SpeciesNotFoundError(PlantEError):
    """A espécie solicitada não existe."""
    code = "PLANTE_4014_SPECIES_NOT_FOUND"
    status_code = 404

    def __init__(self, species: UUID | str):  # ID ou nome científico
        super().__init__(
            message=f"Species {species} not found.",
        )
