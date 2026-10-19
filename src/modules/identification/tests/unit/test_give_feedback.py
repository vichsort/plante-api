from uuid import UUID

import pytest

from src.modules.identification.domain.exceptions import IdentificationNotFoundError
from src.modules.identification.domain.use_cases.give_feedback import (
    GiveIdentificationFeedbackInputDTO,
    GiveIdentificationFeedbackUseCase,
)
from src.modules.identification.tests.fakes import (
    FakeIdentificationUnitOfWork,
    InMemoryIdentificationRepository,
    make_identification,
)
from src.modules.training import FeedbackOrigin, FeedbackVerdict, IdentificationLabel
from src.modules.training.tests.fakes import FakeTrainingRecorder
from src.shared.domain import UserId

OWNER = UserId(UUID(int=1))


async def test_feedback_is_recorded_on_the_training_sample_with_the_suggestion() -> None:
    # Arrange
    identification = make_identification(user_id=OWNER)
    uow = FakeIdentificationUnitOfWork(InMemoryIdentificationRepository(identification))
    training = FakeTrainingRecorder()
    dto = GiveIdentificationFeedbackInputDTO(
        user_id=OWNER, identification_id=identification.id, verdict=FeedbackVerdict.WRONG, suggested_name="Monstera adansonii",
    )

    # Act
    await GiveIdentificationFeedbackUseCase(uow, training).execute(dto)

    # Assert
    (feedback,) = training.feedback
    assert feedback.target == IdentificationLabel(identification.training_sample_id, "Monstera adansonii")
    assert (feedback.verdict, feedback.origin) == (FeedbackVerdict.WRONG, FeedbackOrigin.EXPLICIT)
    assert uow.commits == 1


async def test_feedback_on_someone_elses_identification_is_not_found() -> None:
    # Arrange
    identification = make_identification(user_id=OWNER)
    uow = FakeIdentificationUnitOfWork(InMemoryIdentificationRepository(identification))
    training = FakeTrainingRecorder()
    dto = GiveIdentificationFeedbackInputDTO(
        user_id=UserId(UUID(int=2)), identification_id=identification.id, verdict=FeedbackVerdict.CORRECT,
    )

    # Act & Assert
    with pytest.raises(IdentificationNotFoundError):
        await GiveIdentificationFeedbackUseCase(uow, training).execute(dto)
    assert training.is_empty
