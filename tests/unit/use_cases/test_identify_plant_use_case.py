from unittest.mock import AsyncMock

import pytest

from src.domain.entities.identification import Identification
from src.domain.exceptions import LowConfidenceError
from src.domain.ports.plant_identifier import IdentificationResult
from src.domain.use_cases.identify_plant_use_case import (
    IdentifyPlantInputDTO,
    IdentifyPlantUseCase,
)
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.modules.training import TrainingIdentificationSample
from src.modules.training.tests.fakes import FakeTrainingRecorder
from tests.factories import (
    CALENDAR,
    make_identification_signals,
    make_species,
    make_user,
)
from tests.fakes import FakeUnitOfWork, MarkingSanitizer


def _recorder(use_case: IdentifyPlantUseCase) -> FakeTrainingRecorder:
    assert isinstance(use_case.training, FakeTrainingRecorder)
    return use_case.training


def _use_case(confidence: float = 0.9):
    user = make_user()
    users = AsyncMock()
    users.get_by_id.return_value = user
    species = AsyncMock()
    species.get_by_scientific_name.return_value = make_species()
    identifications = AsyncMock()
    identifications.save.side_effect = lambda identification: identification
    uow = FakeUnitOfWork(users=users, species=species, identifications=identifications)

    identifier = AsyncMock()
    identifier.identify.return_value = IdentificationResult(
        scientific_name="Monstera deliciosa",
        confidence=ConfidenceScore(confidence),
        source="consensus",
        family="Araceae",
        signals=make_identification_signals(),
    )
    storage = AsyncMock()
    storage.upload_identification_image.return_value = "identifications/user.jpg"
    storage.upload_training_image.return_value = "training/identifications/copy.jpg"

    use_case = IdentifyPlantUseCase(
        uow=uow,
        sanitizer=MarkingSanitizer(),
        plant_identifier=identifier,
        storage=storage,
        publisher=AsyncMock(),
        calendar=CALENDAR,
        training=FakeTrainingRecorder(),
    )
    return use_case, uow, user, identifier, storage


@pytest.mark.asyncio
async def test_records_identification_and_anonymous_training_sample():
    use_case, uow, user, _, _ = _use_case()

    output = await use_case.execute(IdentifyPlantInputDTO(user_id=user.id, image_bytes=b"img", latitude=-23.5617, longitude=-46.6559))

    sample: TrainingIdentificationSample = _recorder(use_case).identification_samples[0]
    identification: Identification = uow.identifications.save.call_args.args[0]

    # Lado do usuário: dono, foto do usuário e vínculo de mão única para o treino
    assert output.identification_id == identification.id
    assert identification.user_id == user.id
    assert identification.image_key == "identifications/user.jpg"
    assert identification.training_sample_id == sample.id

    # Treino: cópia própria da foto, sinais dos provedores, só o mês e GPS aproximado
    assert sample.image_key == "training/identifications/copy.jpg"
    assert sample.signals == make_identification_signals()
    assert sample.period.day == 1
    assert (sample.location.grid_latitude, sample.location.grid_longitude) == (-23.6, -46.7)
    assert (sample.location.country, sample.location.state) == (user.location.country, user.location.state)


@pytest.mark.asyncio
async def test_identifying_does_not_create_a_garden_plant():
    use_case, uow, user, _, _ = _use_case()

    await use_case.execute(IdentifyPlantInputDTO(user_id=user.id, image_bytes=b"img"))

    uow.user_plants.save.assert_not_called()


@pytest.mark.asyncio
async def test_without_coordinates_training_keeps_only_the_state():
    use_case, uow, user, _, _ = _use_case()

    await use_case.execute(IdentifyPlantInputDTO(user_id=user.id, image_bytes=b"img"))

    location = _recorder(use_case).identification_samples[0].location
    assert (location.grid_latitude, location.grid_longitude) == (None, None)
    assert location.state == user.location.state


@pytest.mark.asyncio
async def test_providers_and_storage_only_receive_the_sanitized_photo():
    use_case, _, user, identifier, storage = _use_case()

    await use_case.execute(IdentifyPlantInputDTO(user_id=user.id, image_bytes=b"img"))

    assert identifier.identify.call_args.kwargs["image_bytes"] == b"clean:img"
    assert storage.upload_identification_image.call_args.kwargs["image_bytes"] == b"clean:img"
    assert storage.upload_training_image.call_args.kwargs["image_bytes"] == b"clean:img"


@pytest.mark.asyncio
async def test_reads_and_writes_in_separate_transactions_and_charges_one_token():
    use_case, uow, user, _, _ = _use_case()

    await use_case.execute(IdentifyPlantInputDTO(user_id=user.id, image_bytes=b"img"))

    # Leitura e escrita em transações separadas (a IA roda entre elas); só a escrita confirma
    assert uow.opened == 2
    assert uow.commits == 1
    assert user.tokens_used_today == 1


@pytest.mark.asyncio
async def test_rejected_confidence_records_nothing():
    use_case, uow, user, _, _ = _use_case(confidence=0.3)

    with pytest.raises(LowConfidenceError):
        await use_case.execute(IdentifyPlantInputDTO(user_id=user.id, image_bytes=b"img"))

    assert uow.commits == 0
    assert _recorder(use_case).is_empty
