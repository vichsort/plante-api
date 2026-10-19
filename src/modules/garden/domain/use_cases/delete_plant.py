from dataclasses import dataclass
from datetime import UTC, datetime

import structlog

from src.modules.garden.domain.exceptions import PlantNotFoundError
from src.modules.garden.domain.ports.unit_of_work import IGardenUnitOfWork
from src.modules.garden.domain.value_objects.ids import UserPlantId
from src.modules.garden.domain.value_objects.removal_reason import RemovalReason
from src.modules.identification import (
    IdentificationId,
    IdentificationNotFoundError,
    IIdentificationLookup,
)
from src.modules.training import (
    FeedbackOrigin,
    FeedbackVerdict,
    IdentificationLabel,
    ITrainingRecorder,
)
from src.shared.domain import UserId

log = structlog.stdlib.get_logger()

# Reason -> the implicit signal on the identification label
_SIGNAL: dict[RemovalReason, tuple[FeedbackVerdict, FeedbackOrigin]] = {
    RemovalReason.MISIDENTIFIED: (FeedbackVerdict.WRONG, FeedbackOrigin.REMOVED_MISIDENTIFIED),
    RemovalReason.DIED: (FeedbackVerdict.UNSURE, FeedbackOrigin.REMOVED_DIED),
    RemovalReason.GAVE_AWAY: (FeedbackVerdict.UNSURE, FeedbackOrigin.REMOVED_GAVE_AWAY),
    RemovalReason.OTHER: (FeedbackVerdict.UNSURE, FeedbackOrigin.REMOVED_OTHER),
}


@dataclass(frozen=True)
class DeleteUserPlantInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId
    reason: RemovalReason | None = None


class DeleteUserPlantUseCase:
    """
    Takes the plant out of the garden (soft delete). Without a reason, the dataset is untouched:
    the plant may have died or been given away. With one, it becomes an implicit signal on the
    identification label, in the same transaction; only `misidentified` votes against it.
    """

    raises = (PlantNotFoundError,)

    def __init__(self, uow: IGardenUnitOfWork, training: ITrainingRecorder, identifications: IIdentificationLookup) -> None:
        self.uow = uow
        self.training = training
        self.identifications = identifications

    async def execute(self, dto: DeleteUserPlantInputDTO) -> None:
        async with self.uow as uow:
            plant = await uow.user_plants.get_by_id(dto.user_plant_id, dto.user_id)
            if plant is None or not await uow.user_plants.delete(user_plant_id=plant.id, user_id=dto.user_id):
                raise PlantNotFoundError(dto.user_plant_id)
            if dto.reason is not None:
                await self._record_reason(plant.identification_id, dto.user_id, dto.reason)
            await uow.commit()

    async def _record_reason(self, identification_id: IdentificationId, user_id: UserId, reason: RemovalReason) -> None:
        try:
            identification = await self.identifications.get_for_user(identification_id, user_id)
        except IdentificationNotFoundError:
            # The plant still goes; there is just no sample left to attach the signal to
            log.warning("garden.removal_reason_without_identification", identification_id=str(identification_id))
            return
        verdict, origin = _SIGNAL[reason]
        await self.training.record_feedback(
            IdentificationLabel(identification.training_sample_id), verdict, origin, given_on=datetime.now(UTC).date(),
        )
