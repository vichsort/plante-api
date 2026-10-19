from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.health.domain.exceptions import HealthRecordNotFoundError
from src.modules.health.domain.ports.unit_of_work import IHealthUnitOfWork
from src.modules.health.domain.value_objects.ids import HealthRecordId
from src.modules.training import (
    FeedbackOrigin,
    FeedbackVerdict,
    HealthLabel,
    ITrainingRecorder,
)
from src.shared.domain import UserId


@dataclass(frozen=True)
class GiveHealthFeedbackInputDTO:
    user_id: UserId
    health_record_id: HealthRecordId
    verdict: FeedbackVerdict


class GiveHealthFeedbackUseCase:
    """Feedback sobre o diagnóstico (acertou / errou / não sei): um evento na amostra de treino de saúde."""

    raises = (HealthRecordNotFoundError,)

    def __init__(self, uow: IHealthUnitOfWork, training: ITrainingRecorder) -> None:
        self.uow = uow
        self.training = training

    async def execute(self, dto: GiveHealthFeedbackInputDTO) -> None:
        async with self.uow as uow:
            record = await uow.health_records.get_for_user(dto.health_record_id, dto.user_id)
            if record is None:
                raise HealthRecordNotFoundError(dto.health_record_id)

            await self.training.record_feedback(
                HealthLabel(record.training_sample_id),
                dto.verdict,
                FeedbackOrigin.EXPLICIT,
                given_on=datetime.now(UTC).date(),
            )
            await uow.commit()
