from dependency_injector import containers, providers

from src.adapters.persistence.repositories.user_repository import UserRepository
from src.adapters.persistence.repositories.user_plant_repository import UserPlantRepository
from src.adapters.persistence.repositories.plant_species_repository import PlantSpeciesRepository
from src.adapters.persistence.repositories.plant_nutritional_repository import PlantNutritionalRepository
from src.adapters.persistence.repositories.plant_reference_image_repository import PlantReferenceImageRepository
from src.adapters.persistence.repositories.health_record_repository import HealthRecordRepository
from src.adapters.persistence.repositories.identification_sample_repository import IdentificationSampleRepository
from src.adapters.persistence.repositories.achievement_repository import AchievementRepository
from src.adapters.persistence.repositories.health_identification_sample_repository import HealthIdentificationSampleRepository

class RepositoriesContainer(containers.DeclarativeContainer):
    session = providers.Dependency()
    
    user_repository = providers.Factory(
        UserRepository,
        session=session,
    )

    user_plant_repository = providers.Factory(
        UserPlantRepository,
        session=session,
    )

    health_record_repository = providers.Factory(
        HealthRecordRepository,
        session=session,
    )

    health_identification_sample_repository = providers.Factory(
        HealthIdentificationSampleRepository,
        session=session,
    )

    plant_species_repository = providers.Factory(
        PlantSpeciesRepository,
        session=session,
    )

    plant_nutritional_repository = providers.Factory(
        PlantNutritionalRepository,
        session=session,
    )

    plant_reference_image_repository = providers.Factory(
        PlantReferenceImageRepository,
        session=session,
    )

    health_record_repository = providers.Factory(
        HealthRecordRepository,
        session=session,
    )

    identification_sample_repository = providers.Factory(
        IdentificationSampleRepository,
        session=session,
    )

    achievement_repository = providers.Factory(
        AchievementRepository, 
        session=session
    )