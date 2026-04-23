from dataclasses import dataclass

from src.domain.events.domain_events import PlantAddedToGardenEvent
from src.domain.exceptions import UserNotFoundError, PlantNotFoundError, ForbiddenError, SpeciesNotFoundError
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.user_repository import IUserRepository

@dataclass(frozen=True)
class AddPlantToGardenInputDTO:
    user_id: int
    user_plant_id: int

class AddPlantToGardenUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        user_plant_repo: IUserPlantRepository,
        species_repo: IPlantSpeciesRepository,
        publisher: IDomainPublisher,
    ) -> None:
        self.user_repo = user_repo
        self.user_plant_repo = user_plant_repo
        self.species_repo = species_repo
        self.publisher = publisher

    async def execute(self, dto: AddPlantToGardenInputDTO) -> None:
        user = await self.user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(dto.user_id)

        user_plant = await self.user_plant_repo.get_by_id(dto.user_plant_id)
        if user_plant is None:
            raise PlantNotFoundError(dto.user_plant_id)

        if user_plant.user_id != dto.user_id:
            raise ForbiddenError("You dont have the permission to add this plant to your garden.")

        species = await self.species_repo.get_by_scientific_name(user_plant.scientific_name)
        if species is None:
            raise SpeciesNotFoundError(user_plant.scientific_name)

        SubscriptionPolicy.enforce_can_add_to_garden(user)

        is_first = user.garden_count == 0
        user.add_plant_to_garden()
        await self.user_repo.save(user)

        await self.publisher.publish(
            PlantAddedToGardenEvent.create(
                user_id=user.id,
                user_plant_id=user_plant.id,
                species_id=species.id,
                is_first_plant=is_first,
            )
        )