from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.events.domain_events import PlantAddedToGardenEvent
from src.domain.exceptions import (
    ForbiddenError,
    PlantLimitExceededError,
    PlantNotFoundError,
    SampleNotFoundError,
    SpeciesNotFoundError,
    UserNotFoundError,
)
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import IdentificationSampleId, UserId, UserPlantId


@dataclass(frozen=True)
class AddPlantToGardenInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId
    sample_id: IdentificationSampleId

class AddPlantToGardenUseCase:
    raises = (
        ForbiddenError,
        PlantLimitExceededError,
        PlantNotFoundError,
        SampleNotFoundError,
        SpeciesNotFoundError,
        UserNotFoundError,
    )

    def __init__(
        self,
        uow: IUnitOfWork,
        publisher: IDomainPublisher,
    ) -> None:
        self.uow = uow
        self.publisher = publisher

    async def execute(self, dto: AddPlantToGardenInputDTO) -> None:
        now = datetime.now(UTC)

        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)

            user_plant = await uow.user_plants.get_by_id(dto.user_plant_id)
            if user_plant is None:
                raise PlantNotFoundError(dto.user_plant_id)

            if user_plant.user_id != dto.user_id:
                raise ForbiddenError("Você não tem permissão para adicionar esta planta.")

            species = await uow.species.get_by_scientific_name(user_plant.scientific_name)
            if species is None:
                raise SpeciesNotFoundError(user_plant.scientific_name)

            sample = await uow.identification_samples.get_by_id(dto.sample_id)
            if sample is None:
                raise SampleNotFoundError(dto.sample_id)

            SubscriptionPolicy.enforce_can_add_to_garden(user)

            is_first = user.garden_count == 0
            user.add_plant_to_garden()

            await uow.users.save(user)
            await uow.identification_samples.save(sample.confirm(confirmed_at=now))
            await uow.commit()

        await self.publisher.publish(
            PlantAddedToGardenEvent.create(
                user_id=user.id,
                user_plant_id=user_plant.id,
                species_id=species.id,
                is_first_plant=is_first,
            )
        )
