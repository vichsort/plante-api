from unittest.mock import AsyncMock

import pytest

from src.domain.entities.user_plant import IdentificationSource
from src.domain.ports.plant_identifier import IdentificationResult
from src.domain.use_cases.identify_plant_use_case import (
    IdentifyPlantInputDTO,
    IdentifyPlantUseCase,
)
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.sources import IdentificationOrigin
from tests.factories import make_species, make_user
from tests.fakes import FakeUnitOfWork


@pytest.mark.asyncio
@pytest.mark.parametrize("origin, expected", [
    ("kindwise", IdentificationSource.KINDWISE),
    ("plantnet", IdentificationSource.PLANTNET),  # antes virava CONSENSUS
    ("consensus", IdentificationSource.CONSENSUS),
    ("consensus_partial", IdentificationSource.CONSENSUS),
])
async def test_identification_source_follows_origin(origin: IdentificationOrigin, expected: IdentificationSource):
    user = make_user()
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user
    species_repo = AsyncMock()
    species_repo.get_by_scientific_name.return_value = make_species()
    user_plant_repo = AsyncMock()
    user_plant_repo.save.side_effect = lambda plant: plant
    sample_repo = AsyncMock()
    sample_repo.save.side_effect = lambda sample: sample
    identifier = AsyncMock()
    identifier.identify.return_value = IdentificationResult(
        scientific_name="Monstera deliciosa",
        confidence=ConfidenceScore(0.9),
        source=origin,
    )
    storage = AsyncMock()
    storage.upload_identification_image.return_value = "identifications/key.jpg"

    uow = FakeUnitOfWork(users=user_repo, species=species_repo, user_plants=user_plant_repo, reference_images=AsyncMock(), identification_samples=sample_repo)
    use_case = IdentifyPlantUseCase(
        uow=uow,
        plant_identifier=identifier,
        storage=storage,
        publisher=AsyncMock(),
    )

    await use_case.execute(IdentifyPlantInputDTO(user_id=user.id, image_bytes=b"img"))

    saved_plant = user_plant_repo.save.call_args.args[0]
    assert saved_plant.identification_source == expected
    assert sample_repo.save.call_args.args[0].identification_source == origin
    # Leitura e escrita em transações separadas (a IA roda entre elas); só a escrita confirma
    assert uow.opened == 2
    assert uow.commits == 1
