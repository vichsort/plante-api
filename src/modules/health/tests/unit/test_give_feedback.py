from uuid import uuid4

import pytest

from src.modules.health.domain.exceptions import HealthRecordNotFoundError
from src.modules.health.domain.use_cases.give_feedback import (
    GiveHealthFeedbackInputDTO,
    GiveHealthFeedbackUseCase,
)
from src.modules.health.tests.fakes import (
    FakeHealthUnitOfWork,
    InMemoryHealthRecordRepository,
    make_health_record,
)
from src.modules.training import FeedbackOrigin, FeedbackVerdict, HealthLabel
from src.modules.training.tests.fakes import FakeTrainingRecorder
from src.shared.domain import UserId


async def test_feedback_labels_the_training_sample_of_the_diagnosis() -> None:
    # Arrange
    record = make_health_record()
    training = FakeTrainingRecorder()
    uow = FakeHealthUnitOfWork(InMemoryHealthRecordRepository(record))
    assert record.user_id is not None

    # Act
    await GiveHealthFeedbackUseCase(uow, training).execute(
        GiveHealthFeedbackInputDTO(user_id=record.user_id, health_record_id=record.id, verdict=FeedbackVerdict.WRONG)
    )

    # Assert
    (feedback,) = training.feedback
    assert feedback.target == HealthLabel(record.training_sample_id)
    assert (feedback.verdict, feedback.origin) == (FeedbackVerdict.WRONG, FeedbackOrigin.EXPLICIT)
    assert uow.commits == 1


async def test_feedback_on_a_diagnosis_of_another_user_is_not_found() -> None:
    # Arrange
    record = make_health_record()
    training = FakeTrainingRecorder()
    uow = FakeHealthUnitOfWork(InMemoryHealthRecordRepository(record))

    # Act & Assert
    with pytest.raises(HealthRecordNotFoundError):
        await GiveHealthFeedbackUseCase(uow, training).execute(
            GiveHealthFeedbackInputDTO(user_id=UserId(uuid4()), health_record_id=record.id, verdict=FeedbackVerdict.CORRECT)
        )
    assert training.is_empty
    assert uow.commits == 0
