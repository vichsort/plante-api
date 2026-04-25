from dataclasses import dataclass
from datetime import datetime, timezone

from src.domain.entities.plant_identification_sample import SampleStatus
from src.domain.events.domain_events import PlantIdentificationConfirmedEvent
from src.domain.exceptions import SampleNotFoundError, UserNotFoundError
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.identification_sample_repository import IIdentificationSampleRepository
from src.domain.ports.user_repository import IUserRepository

@dataclass(frozen=True)
class ConfirmPlantIdentificationInputDTO:
    user_id: int
    sample_id: int

class ConfirmPlantIdentificationUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        sample_repo: IIdentificationSampleRepository,
        publisher: IDomainPublisher,
    ) -> None:
        self._user_repo = user_repo
        self._sample_repo = sample_repo
        self._publisher = publisher

    async def execute(self, dto: ConfirmPlantIdentificationInputDTO) -> dict:
        now = datetime.now(timezone.utc)

        user = await self._user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(dto.user_id)

        sample = await self._sample_repo.get_by_id(dto.sample_id)
        if sample is None or sample.user_id != dto.user_id:
            raise SampleNotFoundError(dto.sample_id)

        confirmed = sample.confirm(confirmed_at=now)
        await self._sample_repo.save(confirmed)

        await self._publisher.publish(
            PlantIdentificationConfirmedEvent.create(
                user_id=dto.user_id,
                sample_id=confirmed.id,
                scientific_name=confirmed.scientific_name,
            )
        )

        return {
            "sample_id": confirmed.id,
            "scientific_name": confirmed.scientific_name,
            "status": confirmed.status.value,
            "confirmed_at": confirmed.confirmed_at.isoformat(),
        }