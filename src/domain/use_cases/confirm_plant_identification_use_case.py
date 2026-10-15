from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.entities.plant_identification_sample import PlantIdentificationSample
from src.domain.events.domain_events import PlantIdentificationConfirmedEvent
from src.domain.exceptions import SampleNotFoundError, UserNotFoundError
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import IdentificationSampleId, UserId


@dataclass(frozen=True)
class ConfirmPlantIdentificationInputDTO:
    user_id: UserId
    sample_id: IdentificationSampleId

class ConfirmPlantIdentificationUseCase:
    raises = (SampleNotFoundError, UserNotFoundError)

    def __init__(
        self,
        uow: IUnitOfWork,
        publisher: IDomainPublisher,
    ) -> None:
        self._uow = uow
        self._publisher = publisher

    async def execute(self, dto: ConfirmPlantIdentificationInputDTO) -> PlantIdentificationSample:
        now = datetime.now(UTC)

        async with self._uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)

            sample = await uow.identification_samples.get_by_id(dto.sample_id)
            if sample is None or sample.user_id != dto.user_id:
                raise SampleNotFoundError(dto.sample_id)

            confirmed = sample.confirm(confirmed_at=now)
            await uow.identification_samples.save(confirmed)
            await uow.commit()

        await self._publisher.publish(
            PlantIdentificationConfirmedEvent.create(
                user_id=dto.user_id,
                sample_id=confirmed.id,
                scientific_name=confirmed.scientific_name,
            )
        )

        return confirmed
