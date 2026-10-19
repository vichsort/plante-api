from uuid import UUID

from src.shared.domain import PlantEError


class SpeciesNotFoundError(PlantEError):
    """The species does not exist."""
    code = "PLANTE_4330_SPECIES_NOT_FOUND"
    status_code = 404

    def __init__(self, species: UUID | str):  # ID or scientific name
        super().__init__(
            message=f"Species {species} not found.",
        )
