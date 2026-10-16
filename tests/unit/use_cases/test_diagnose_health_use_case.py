import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.domain.entities.user import User
from src.domain.exceptions import SubscriptionRequiredError
from src.domain.ports.health_analyzer import DiseaseHint, HealthAssessmentResult
from src.domain.ports.plant_enricher import HealthDiagnosisEnrichment
from src.domain.use_cases.diagnose_health_use_case import (
    DiagnoseHealthInputDTO,
    DiagnoseHealthUseCase,
)
from src.domain.value_objects.ids import UserPlantId
from src.modules.training import DiseaseSuggestion, HealthSignals
from src.modules.training.tests.fakes import FakeTrainingRecorder
from src.shared.domain import ExternalServiceError, UserId
from tests.factories import CALENDAR, make_user, make_user_plant
from tests.fakes import FakeUnitOfWork, MarkingSanitizer


def _use_case(enricher: AsyncMock) -> tuple[DiagnoseHealthUseCase, User, FakeUnitOfWork]:
    user = make_user()
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    user_plant_repo = AsyncMock()
    user_plant_repo.get_by_id.return_value = make_user_plant(user_id=user.id)

    health_repo = AsyncMock()
    health_repo.save.side_effect = lambda record: record

    analyzer = AsyncMock()
    analyzer.assess_health.return_value = HealthAssessmentResult(
        is_healthy=False,
        health_probability=0.1,
        diseases=(DiseaseHint("leaf_spots", 0.8, ("https://kindwise/ref.jpg",)),),
        signals=HealthSignals(provider="kindwise", is_healthy_probability=0.1, diseases=(DiseaseSuggestion("leaf_spots", 0.8),)),
    )

    storage = AsyncMock()
    storage.upload_identification_image.return_value = "health/key.jpg"
    storage.upload_training_image.return_value = "training/identifications/health.jpg"
    storage.download_and_rehost.return_value = "species/references/ref.jpg"
    uow = FakeUnitOfWork(users=user_repo, user_plants=user_plant_repo, health_records=health_repo)

    use_case = DiagnoseHealthUseCase(
        sanitizer=MarkingSanitizer(),
        uow=uow,
        health_analyzer=analyzer,
        plant_enricher=enricher,
        storage=storage,
        calendar=CALENDAR,
        training=FakeTrainingRecorder(),
    )
    return use_case, user, uow


def _dto() -> DiagnoseHealthInputDTO:
    return DiagnoseHealthInputDTO(
        user_id=UserId(uuid.uuid4()),
        user_plant_id=UserPlantId(uuid.uuid4()),
        image_bytes=b"img",
        latitude=-27.5954,
        longitude=-48.548,
    )


@pytest.mark.asyncio
async def test_diagnose_uses_gemini_and_charges_extra_token():
    enricher = AsyncMock()
    enricher.diagnose_health.return_value = HealthDiagnosisEnrichment(vitality_score=0.5, treatment_plan=("water less",))
    use_case, user, _ = _use_case(enricher)

    result = await use_case.execute(_dto())

    assert result.record.treatment_plan == ("water less",)
    assert result.record.vitality_score == 0.5
    assert result.record.source == "kindwise+gemini"
    assert user.tokens_used_today == 2


@pytest.mark.asyncio
async def test_diagnose_degrades_to_kindwise_when_gemini_fails():
    enricher = AsyncMock()
    enricher.diagnose_health.side_effect = ExternalServiceError(service="Gemini", retryable=True)
    use_case, user, _ = _use_case(enricher)

    result = await use_case.execute(_dto())

    assert result.record.vitality_score == 0.1
    assert result.record.treatment_plan == ()
    assert result.record.source == "kindwise"
    assert user.tokens_used_today == 1


@pytest.mark.asyncio
async def test_diagnosis_records_anonymous_training_sample_linked_one_way():
    enricher = AsyncMock()
    enricher.diagnose_health.return_value = HealthDiagnosisEnrichment(vitality_score=0.5, treatment_plan=("water less",))
    use_case, _, uow = _use_case(enricher)

    result = await use_case.execute(_dto())

    assert isinstance(use_case._training, FakeTrainingRecorder)
    sample = use_case._training.health_samples[0]
    assert result.record.training_sample_id == sample.id
    assert sample.image_key == "training/identifications/health.jpg"
    assert sample.image_key != result.record.image_key
    assert sample.reference_image_keys == ("species/references/ref.jpg",)
    assert sample.signals.diseases == (DiseaseSuggestion("leaf_spots", 0.8),)
    assert (sample.location.grid_latitude, sample.location.grid_longitude) == (-27.6, -48.5)
    assert sample.period.day == 1
    assert uow.committed


@pytest.mark.asyncio
async def test_diagnosis_without_tokens_is_refused_before_calling_providers():
    # Arrange: antes o /diagnose não conferia o saldo e gastava créditos dos provedores
    enricher = AsyncMock()
    use_case, user, _ = _use_case(enricher)
    user.tokens_used_today, user.tokens_day = 3, CALENDAR.date_of(datetime.now(UTC))

    # Act & Assert
    with pytest.raises(SubscriptionRequiredError):
        await use_case.execute(_dto())
    enricher.diagnose_health.assert_not_called()


@pytest.mark.asyncio
async def test_last_token_buys_the_diagnosis_without_gemini():
    # Arrange: sobra 1 token; o complemento custaria mais 1
    enricher = AsyncMock()
    use_case, user, _ = _use_case(enricher)
    user.tokens_used_today, user.tokens_day = 2, CALENDAR.date_of(datetime.now(UTC))

    # Act
    result = await use_case.execute(_dto())

    # Assert
    enricher.diagnose_health.assert_not_called()
    assert result.record.source == "kindwise"
    assert user.tokens_used_today == 3
