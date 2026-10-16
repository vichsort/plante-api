from src.modules.catalog.domain.ports.nutritional_repository import (
    IPlantNutritionalRepository,
)
from src.modules.catalog.domain.ports.reference_image_repository import (
    IPlantReferenceImageRepository,
)
from src.modules.catalog.domain.ports.species_repository import IPlantSpeciesRepository
from src.shared.domain import IUnitOfWork


class ICatalogUnitOfWork(IUnitOfWork):
    """O catálogo dentro da transação de quem grava (regras em `src.shared.domain.IUnitOfWork`)."""

    species: IPlantSpeciesRepository
    reference_images: IPlantReferenceImageRepository
    nutritional: IPlantNutritionalRepository
