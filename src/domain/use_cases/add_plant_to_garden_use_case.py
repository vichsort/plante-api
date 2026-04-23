from dataclasses import dataclass
from datetime import datetime, timezone

from src.domain.events.domain_events import PlantAddedToGardenEvent
from src.domain.exceptions import (
    UserNotFoundError,
    PlantNotFoundError,
    ForbiddenError,
    SpeciesNotFoundError,
    SampleNotFoundError,
)
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.identification_sample_repository import IIdentificationSampleRepository
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.user_repository import IUserRepository

@dataclass(frozen=True)
class AddPlantToGardenInputDTO:
    user_id: int
    user_plant_id: int
    sample_id: int  # retornado pelo IdentifyPlantUseCase

class AddPlantToGardenUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        user_plant_repo: IUserPlantRepository,
        species_repo: IPlantSpeciesRepository,
        sample_repo: IIdentificationSampleRepository,
        publisher: IDomainPublisher,
    ) -> None:
        self.user_repo = user_repo
        self.user_plant_repo = user_plant_repo
        self.species_repo = species_repo
        self.sample_repo = sample_repo
        self.publisher = publisher

    async def execute(self, dto: AddPlantToGardenInputDTO) -> None:
        now = datetime.now(timezone.utc)

        user = await self.user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(dto.user_id)

        user_plant = await self.user_plant_repo.get_by_id(dto.user_plant_id)
        if user_plant is None:
            raise PlantNotFoundError(dto.user_plant_id)

        if user_plant.user_id != dto.user_id:
            raise ForbiddenError("Você não tem permissão para adicionar esta planta.")

        species = await self.species_repo.get_by_scientific_name(user_plant.scientific_name)
        if species is None:
            raise SpeciesNotFoundError(user_plant.scientific_name)

        sample = await self.sample_repo.get_by_id(dto.sample_id)
        if sample is None:
            raise SampleNotFoundError(dto.sample_id)

        SubscriptionPolicy.enforce_can_add_to_garden(user)

        is_first = user.garden_count == 0
        user.add_plant_to_garden()

        confirmed_sample = sample.confirm(confirmed_at=now)

        await self.user_repo.save(user)
        await self.sample_repo.save(confirmed_sample)

        await self.publisher.publish(
            PlantAddedToGardenEvent.create(
                user_id=user.id,
                user_plant_id=user_plant.id,
                species_id=species.id,
                is_first_plant=is_first,
            )
        )