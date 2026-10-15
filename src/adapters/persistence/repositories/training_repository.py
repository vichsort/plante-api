from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.mappers.training_mapper import TrainingMapper
from src.adapters.persistence.models import (
    TrainingFeedbackModel,
    TrainingHealthSampleModel,
    TrainingIdentificationSampleModel,
)
from src.domain.entities.training import (
    TrainingFeedback,
    TrainingHealthSample,
    TrainingIdentificationSample,
)
from src.domain.ports.training_repository import ITrainingRepository
from src.domain.value_objects.ids import (
    TrainingHealthSampleId,
    TrainingIdentificationSampleId,
)


class TrainingRepository(ITrainingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_identification_sample(self, sample: TrainingIdentificationSample) -> None:
        self._session.add(TrainingMapper.identification_to_model(sample))
        await self._session.flush()

    async def add_health_sample(self, sample: TrainingHealthSample) -> None:
        self._session.add(TrainingMapper.health_to_model(sample))
        await self._session.flush()

    async def add_feedback(self, feedback: TrainingFeedback) -> None:
        self._session.add(TrainingMapper.feedback_to_model(feedback))
        await self._session.flush()

    async def get_identification_sample(
        self, sample_id: TrainingIdentificationSampleId
    ) -> TrainingIdentificationSample | None:
        model = await self._session.get(TrainingIdentificationSampleModel, sample_id)
        return TrainingMapper.identification_to_domain(model) if model else None

    async def get_health_sample(self, sample_id: TrainingHealthSampleId) -> TrainingHealthSample | None:
        model = await self._session.get(TrainingHealthSampleModel, sample_id)
        return TrainingMapper.health_to_domain(model) if model else None

    async def list_feedback(
        self, sample_id: TrainingIdentificationSampleId | TrainingHealthSampleId
    ) -> list[TrainingFeedback]:
        # Sem horário exato: dentro do mesmo dia, a ordem de inserção não é garantida
        stmt = (
            select(TrainingFeedbackModel)
            .where(or_(
                TrainingFeedbackModel.identification_sample_id == sample_id,
                TrainingFeedbackModel.health_sample_id == sample_id,
            ))
            .order_by(TrainingFeedbackModel.given_on)
        )
        result = await self._session.execute(stmt)
        return [TrainingMapper.feedback_to_domain(m) for m in result.scalars().all()]
