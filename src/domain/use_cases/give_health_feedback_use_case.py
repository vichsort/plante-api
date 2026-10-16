from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.entities.training import FeedbackVerdict, TrainingFeedback
from src.domain.exceptions import HealthRecordNotFoundError
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import HealthRecordId
from src.shared.domain import UserId


@dataclass(frozen=True)
class GiveHealthFeedbackInputDTO:
    user_id: UserId
    health_record_id: HealthRecordId
    verdict: FeedbackVerdict


class GiveHealthFeedbackUseCase:
    """Feedback sobre o diagnóstico (acertou / errou / não sei): um evento na amostra de treino de saúde."""

    raises = (HealthRecordNotFoundError,)

    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: GiveHealthFeedbackInputDTO) -> None:
        async with self.uow as uow:
            record = await uow.health_records.get_by_id(dto.health_record_id)
            if record is None or record.user_id != dto.user_id:
                raise HealthRecordNotFoundError(dto.health_record_id)

            await uow.training.add_feedback(TrainingFeedback.on_health(
                sample_id=record.training_sample_id,
                verdict=dto.verdict,
                given_on=datetime.now(UTC).date(),
            ))
            await uow.commit()
