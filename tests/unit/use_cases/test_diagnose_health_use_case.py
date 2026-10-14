import dataclasses
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.entities.user import User
from src.domain.exceptions import ExternalServiceError
from src.domain.ports.health_analyzer import HealthAssessmentResult
from src.domain.use_cases.diagnose_health_use_case import (
    DiagnoseHealthInputDTO,
    DiagnoseHealthUseCase,
)
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.domain.value_objects.user_location import UserLocation


def _use_case(enricher: AsyncMock) -> tuple[DiagnoseHealthUseCase, User]:
    user = User(
        id=str(uuid.uuid4()),
        email="user@plante.org",
        hashed_password="hashed",
        location=UserLocation(country="BR", state="SP"),
        is_verified=True,
        subscription=SubscriptionTier.FREE,
        created_at=datetime.now(UTC),
    )
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    user_plant_repo = AsyncMock()
    user_plant_repo.get_by_id.return_value = MagicMock(scientific_name="Monstera deliciosa")

    health_repo = AsyncMock()
    health_repo.save.side_effect = lambda record: dataclasses.replace(record, id="record-1")

    analyzer = AsyncMock()
    analyzer.assess_health.return_value = HealthAssessmentResult(
        is_healthy=False, health_probability=0.1, diseases=(), raw_response={}
    )

    storage = AsyncMock()
    storage.upload_identification_image.return_value = "health/key.jpg"

    use_case = DiagnoseHealthUseCase(
        user_repo=user_repo,
        user_plant_repo=user_plant_repo,
        health_repo=health_repo,
        health_analyzer=analyzer,
        plant_enricher=enricher,
        storage=storage,
        health_raw_repo=AsyncMock(),
    )
    return use_case, user


def _dto() -> DiagnoseHealthInputDTO:
    return DiagnoseHealthInputDTO(user_id="u", user_plant_id="p", image_bytes=b"img")


@pytest.mark.asyncio
async def test_diagnose_uses_gemini_and_charges_extra_token():
    enricher = AsyncMock()
    enricher.diagnose_health.return_value = {"vitality_score": 0.5, "treatment_plan": ["water less"]}
    use_case, user = _use_case(enricher)

    result = await use_case.execute(_dto())

    assert result["treatment_plan"] == ["water less"]
    assert result["vitality_score"] == 0.5
    assert user.tokens_used_today == 2


@pytest.mark.asyncio
async def test_diagnose_degrades_to_kindwise_when_gemini_fails():
    enricher = AsyncMock()
    enricher.diagnose_health.side_effect = ExternalServiceError(service="Gemini", retryable=True)
    use_case, user = _use_case(enricher)

    result = await use_case.execute(_dto())

    assert result["vitality_score"] == 0.1
    assert result["treatment_plan"] == []
    assert user.tokens_used_today == 1
