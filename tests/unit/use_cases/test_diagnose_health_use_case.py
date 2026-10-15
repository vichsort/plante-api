import uuid
from unittest.mock import AsyncMock

import pytest

from src.domain.entities.user import User
from src.domain.exceptions import ExternalServiceError
from src.domain.ports.health_analyzer import HealthAssessmentResult
from src.domain.ports.plant_enricher import HealthDiagnosisEnrichment
from src.domain.use_cases.diagnose_health_use_case import (
    DiagnoseHealthInputDTO,
    DiagnoseHealthUseCase,
)
from src.domain.value_objects.ids import UserId, UserPlantId
from tests.factories import make_user, make_user_plant
from tests.fakes import FakeUnitOfWork, MarkingSanitizer


def _use_case(enricher: AsyncMock) -> tuple[DiagnoseHealthUseCase, User]:
    user = make_user()
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    user_plant_repo = AsyncMock()
    user_plant_repo.get_by_id.return_value = make_user_plant(user_id=user.id)

    health_repo = AsyncMock()
    health_repo.save.side_effect = lambda record: record

    analyzer = AsyncMock()
    analyzer.assess_health.return_value = HealthAssessmentResult(
        is_healthy=False, health_probability=0.1, diseases=(), raw_response={}
    )

    storage = AsyncMock()
    storage.upload_identification_image.return_value = "health/key.jpg"

    use_case = DiagnoseHealthUseCase(
        sanitizer=MarkingSanitizer(),
        uow=FakeUnitOfWork(users=user_repo, user_plants=user_plant_repo, health_records=health_repo),
        health_analyzer=analyzer,
        plant_enricher=enricher,
        storage=storage,
        health_raw_repo=AsyncMock(),
    )
    return use_case, user


def _dto() -> DiagnoseHealthInputDTO:
    return DiagnoseHealthInputDTO(user_id=UserId(uuid.uuid4()), user_plant_id=UserPlantId(uuid.uuid4()), image_bytes=b"img")


@pytest.mark.asyncio
async def test_diagnose_uses_gemini_and_charges_extra_token():
    enricher = AsyncMock()
    enricher.diagnose_health.return_value = HealthDiagnosisEnrichment(vitality_score=0.5, treatment_plan=("water less",))
    use_case, user = _use_case(enricher)

    result = await use_case.execute(_dto())

    assert result.record.treatment_plan == ("water less",)
    assert result.record.vitality_score == 0.5
    assert result.record.source == "kindwise+gemini"
    assert user.tokens_used_today == 2


@pytest.mark.asyncio
async def test_diagnose_degrades_to_kindwise_when_gemini_fails():
    enricher = AsyncMock()
    enricher.diagnose_health.side_effect = ExternalServiceError(service="Gemini", retryable=True)
    use_case, user = _use_case(enricher)

    result = await use_case.execute(_dto())

    assert result.record.vitality_score == 0.1
    assert result.record.treatment_plan == ()
    assert result.record.source == "kindwise"
    assert user.tokens_used_today == 1
