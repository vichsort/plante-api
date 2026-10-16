from src.domain.ports.achievement_repository import IAchievementRepository
from src.domain.ports.health_record_repository import IHealthRecordRepository
from src.domain.ports.identification_repository import IIdentificationRepository
from src.domain.ports.plant_nutritional_repository import IPlantNutritionalRepository
from src.domain.ports.plant_reference_image_repository import (
    IPlantReferenceImageRepository,
)
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.user_repository import IUserRepository
from src.shared.domain import IUnitOfWork as SharedUnitOfWork


class IUnitOfWork(SharedUnitOfWork):
    """
    UoW do código em camadas antigo (regras em `src.shared.domain.IUnitOfWork`). Perde um
    repositório a cada módulo migrado; cada módulo tem a própria porta de UoW.
    """

    users: IUserRepository
    user_plants: IUserPlantRepository
    species: IPlantSpeciesRepository
    nutritional: IPlantNutritionalRepository
    reference_images: IPlantReferenceImageRepository
    identifications: IIdentificationRepository
    health_records: IHealthRecordRepository
    achievements: IAchievementRepository
