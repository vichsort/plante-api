from dataclasses import dataclass, field
from uuid import UUID

import pytest

from src.modules.catalog.tests.fakes import FakeSpeciesRegistry
from src.modules.identification.domain.events import PlantIdentifiedEvent
from src.modules.identification.domain.exceptions import LowConfidenceError
from src.modules.identification.domain.use_cases.identify_plant import (
    IdentifyPlantInputDTO,
    IdentifyPlantUseCase,
)
from src.modules.identification.tests.fakes import (
    FakeIdentificationUnitOfWork,
    StubPlantIdentifier,
    make_result,
)
from src.modules.identity import UserLocation
from src.modules.identity.tests.fakes import FakeUserDirectory
from src.modules.subscription import FeatureCost, SubscriptionRequiredError
from src.modules.subscription.tests.fakes import FakeTokenWallet
from src.modules.training.tests.fakes import FakeTrainingRecorder
from src.shared.domain import UserId
from src.shared.tests.fakes import (
    MarkingSanitizer,
    RecordingImageStorage,
    RecordingPublisher,
)

USER = UserId(UUID(int=1))


@dataclass
class _Scenario:
    """O use case com todas as portas em memória, para o teste olhar o estado de cada uma."""
    confidence: float = 0.9
    used_today: int = 0
    uow: FakeIdentificationUnitOfWork = field(default_factory=FakeIdentificationUnitOfWork)
    identifier: StubPlantIdentifier = field(init=False)
    storage: RecordingImageStorage = field(default_factory=RecordingImageStorage)
    publisher: RecordingPublisher = field(default_factory=RecordingPublisher)
    wallet: FakeTokenWallet = field(init=False)
    training: FakeTrainingRecorder = field(default_factory=FakeTrainingRecorder)
    catalog: FakeSpeciesRegistry = field(default_factory=FakeSpeciesRegistry)
    location: UserLocation = field(default_factory=lambda: UserLocation(country="BR", state="SP"))

    def __post_init__(self) -> None:
        self.identifier = StubPlantIdentifier(make_result(confidence=self.confidence))
        self.wallet = FakeTokenWallet(used_today=self.used_today)

    def use_case(self) -> IdentifyPlantUseCase:
        return IdentifyPlantUseCase(
            uow=self.uow,
            sanitizer=MarkingSanitizer(),
            plant_identifier=self.identifier,
            storage=self.storage,
            publisher=self.publisher,
            users=FakeUserDirectory(location=self.location),
            wallet=self.wallet,
            training=self.training,
            catalog=self.catalog,
        )


async def test_records_identification_and_anonymous_training_sample() -> None:
    # Arrange
    scenario = _Scenario()
    dto = IdentifyPlantInputDTO(user_id=USER, image_bytes=b"img", latitude=-23.5617, longitude=-46.6559)

    # Act
    output = await scenario.use_case().execute(dto)

    # Assert: lado do usuário com dono, foto dele e o vínculo de mão única para o treino
    (identification,) = scenario.uow.identifications.by_id.values()
    (sample,) = scenario.training.identification_samples
    assert output.identification_id == identification.id
    assert identification.user_id == USER
    assert identification.image_key == "identifications/1.jpg"
    assert identification.training_sample_id == sample.id
    # Treino: cópia própria da foto, sinais dos provedores, só o mês e GPS aproximado
    assert sample.image_key == "training/identifications/1.jpg"
    assert sample.signals == scenario.identifier.result.signals
    assert sample.period.day == 1
    assert (sample.location.grid_latitude, sample.location.grid_longitude) == (-23.6, -46.7)
    assert (sample.location.country, sample.location.state) == ("BR", "SP")


async def test_without_coordinates_training_keeps_only_the_state() -> None:
    # Arrange
    scenario = _Scenario()

    # Act
    await scenario.use_case().execute(IdentifyPlantInputDTO(user_id=USER, image_bytes=b"img"))

    # Assert
    location = scenario.training.identification_samples[0].location
    assert (location.grid_latitude, location.grid_longitude) == (None, None)
    assert location.state == "SP"


async def test_providers_and_storage_only_receive_the_sanitized_photo() -> None:
    # Arrange
    scenario = _Scenario()

    # Act
    await scenario.use_case().execute(IdentifyPlantInputDTO(user_id=USER, image_bytes=b"img"))

    # Assert
    assert [image for image, _, _ in scenario.identifier.calls] == [b"clean:img"]
    assert scenario.storage.user_uploads == [b"clean:img"]
    assert scenario.storage.training_uploads == [b"clean:img"]


async def test_writes_in_one_transaction_charges_one_token_and_publishes_after_commit() -> None:
    # Arrange
    scenario = _Scenario()

    # Act
    await scenario.use_case().execute(IdentifyPlantInputDTO(user_id=USER, image_bytes=b"img"))

    # Assert: nenhuma transação aberta durante a IA; as leituras são dos outros módulos
    assert (scenario.uow.opened, scenario.uow.commits) == (1, 1)
    assert scenario.wallet.charges == [(USER, FeatureCost.IDENTIFY)]
    assert [type(event) for event in scenario.publisher.events] == [PlantIdentifiedEvent]


async def test_registers_the_species_in_the_catalog() -> None:
    # Arrange
    scenario = _Scenario()

    # Act
    await scenario.use_case().execute(IdentifyPlantInputDTO(user_id=USER, image_bytes=b"img"))

    # Assert
    (identification,) = scenario.uow.identifications.by_id.values()
    assert scenario.catalog.species["Monstera deliciosa"].id == identification.species_id


async def test_identification_without_tokens_is_refused_before_calling_providers() -> None:
    # Arrange
    scenario = _Scenario(used_today=3)

    # Act & Assert
    with pytest.raises(SubscriptionRequiredError):
        await scenario.use_case().execute(IdentifyPlantInputDTO(user_id=USER, image_bytes=b"img"))
    assert scenario.identifier.calls == []
    assert scenario.uow.commits == 0


async def test_rejected_confidence_records_nothing() -> None:
    # Arrange
    scenario = _Scenario(confidence=0.3)

    # Act & Assert
    with pytest.raises(LowConfidenceError):
        await scenario.use_case().execute(IdentifyPlantInputDTO(user_id=USER, image_bytes=b"img"))
    assert scenario.uow.commits == 0
    assert scenario.training.is_empty
    assert scenario.storage.user_uploads == []
