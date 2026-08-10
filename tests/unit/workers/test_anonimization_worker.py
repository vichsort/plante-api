import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.domain.entities.plant_identification_sample import (
    PlantIdentificationSample,
    SampleStatus,
)
from src.infrastructure.container import Container
from src.workers.anonimization_worker import anonymize_confirmed_samples


@pytest.mark.asyncio
async def test_anonymize_confirmed_samples_task():
    user_id = str(uuid.uuid4())
    sample_id = str(uuid.uuid4())
    species_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    sample = PlantIdentificationSample(
        id=sample_id,
        scientific_name="Monstera deliciosa",
        species_id=species_id,
        user_image_key="key",
        identification_confidence=0.9,
        identification_source="consensus",
        raw_response={},
        status=SampleStatus.CONFIRMED,
        created_at=now,
        confirmed_at=now,
        user_id=user_id,
    )

    mock_repo = AsyncMock()
    mock_repo.get_confirmed_before.return_value = [sample]

    container = Container()
    with container.repositories.identification_sample_repository.override(mock_repo):
        result = await anonymize_confirmed_samples(container=container)

    assert result["anonymized"] == 1
    assert result["failed"] == 0
    mock_repo.save.assert_called_once()
