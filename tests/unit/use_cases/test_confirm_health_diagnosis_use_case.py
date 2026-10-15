from unittest.mock import AsyncMock

import pytest

from src.domain.exceptions import HealthRecordNotFoundError
from src.domain.ports.health_raw_response_repository import PendingHealthAssessment
from src.domain.use_cases.confirm_health_diagnosis_use_case import (
    ConfirmHealthDiagnosisInputDTO,
    ConfirmHealthDiagnosisUseCase,
)
from tests.factories import make_health_record, make_user


def _use_case(record_owner_is_caller: bool) -> tuple[ConfirmHealthDiagnosisUseCase, ConfirmHealthDiagnosisInputDTO, AsyncMock]:
    user = make_user()
    record = make_health_record(user_id=user.id if record_owner_is_caller else None)

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user
    record_repo = AsyncMock()
    record_repo.get_by_id.return_value = record
    raw_repo = AsyncMock()
    raw_repo.get.return_value = PendingHealthAssessment(
        raw_response={"result": {}},
        similar_images_urls=("https://kindwise/a.jpg", "https://kindwise/b.jpg"),
    )
    sample_repo = AsyncMock()
    sample_repo.save.side_effect = lambda sample: sample
    storage = AsyncMock()
    storage.download_and_rehost.side_effect = lambda external_url, scientific_name: f"rehosted/{external_url[-5:]}"

    use_case = ConfirmHealthDiagnosisUseCase(
        user_repo=user_repo,
        health_record_repo=record_repo,
        health_sample_repo=sample_repo,
        health_raw_repo=raw_repo,
        storage=storage,
        publisher=AsyncMock(),
    )
    return use_case, ConfirmHealthDiagnosisInputDTO(user_id=user.id, health_record_id=record.id), storage


@pytest.mark.asyncio
async def test_confirm_rehosts_pending_reference_images():
    use_case, dto, storage = _use_case(record_owner_is_caller=True)

    sample = await use_case.execute(dto)

    assert sample.reference_image_keys == ("rehosted/a.jpg", "rehosted/b.jpg")
    assert sample.raw_response == {"result": {}}
    assert storage.download_and_rehost.await_count == 2


@pytest.mark.asyncio
async def test_cannot_confirm_another_users_diagnosis():
    use_case, dto, _ = _use_case(record_owner_is_caller=False)

    with pytest.raises(HealthRecordNotFoundError):
        await use_case.execute(dto)
