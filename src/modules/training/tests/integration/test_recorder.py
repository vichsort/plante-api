"""O `TrainingRecorder` grava dentro da transação de quem chama, e só nela."""
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.training.adapters.persistence.unit_of_work import (
    SqlAlchemyTrainingUnitOfWork,
)
from src.modules.training.domain.entities.feedback import (
    FeedbackOrigin,
    FeedbackVerdict,
    IdentificationLabel,
)
from src.modules.training.domain.services.recorder import TrainingRecorder
from src.modules.training.domain.value_objects.ids import TrainingIdentificationSampleId
from tests.factories import make_training_identification_sample


def _recorder(factory: async_sessionmaker[AsyncSession]) -> TrainingRecorder:
    return TrainingRecorder(SqlAlchemyTrainingUnitOfWork(factory))


async def _count(factory: async_sessionmaker[AsyncSession], table: str) -> int:
    async with factory() as session:
        return int((await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one())


async def test_sample_is_saved_with_the_callers_commit(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    caller = SqlAlchemyTrainingUnitOfWork(session_factory)  # qualquer UoW serve de dono da transação
    sample = make_training_identification_sample("Pilea peperomioides")

    # Act
    async with caller:
        await _recorder(session_factory).record_identification_sample(sample)
        await caller.commit()

    # Assert
    assert await _count(session_factory, "training_identification_samples") == 1


async def test_callers_rollback_takes_the_sample_with_it(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    caller = SqlAlchemyTrainingUnitOfWork(session_factory)

    # Act
    async with caller:
        await _recorder(session_factory).record_identification_sample(make_training_identification_sample("Pilea"))
        # sai sem commit: a identificação falhou, a amostra não pode ficar sozinha

    # Assert
    assert await _count(session_factory, "training_identification_samples") == 0


async def test_recording_outside_a_transaction_fails_loudly(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # Arrange
    recorder = _recorder(session_factory)
    target = IdentificationLabel(TrainingIdentificationSampleId(uuid4()))

    # Act & Assert: sem dono, ninguém confirmaria a gravação; perder em silêncio seria pior
    with pytest.raises(RuntimeError, match="inside the caller's unit of work"):
        await recorder.record_feedback(target, FeedbackVerdict.CORRECT, FeedbackOrigin.EXPLICIT, date(2026, 10, 1))
