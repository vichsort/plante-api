from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from src.modules.garden import PlantNotFoundError, UserPlant, UserPlantId
from src.modules.garden.tests.fakes import FakePlantLookup, make_user_plant
from src.modules.health.domain.use_cases.diagnose import (
    DiagnoseHealthInputDTO,
    DiagnoseHealthUseCase,
)
from src.modules.health.tests.fakes import (
    FakeHealthUnitOfWork,
    StubHealthAnalyzer,
    StubHealthEnricher,
    make_assessment,
)
from src.modules.identity.tests.fakes import FakeUserDirectory
from src.modules.subscription import DailyQuotaExceededError, FeatureCost
from src.modules.subscription.tests.fakes import FakeTokenWallet
from src.modules.training import DiseaseSuggestion, HealthSeverity
from src.modules.training.tests.fakes import FakeTrainingRecorder
from src.shared.domain import ExternalServiceError, UserId, UserNotFoundError
from src.shared.tests.fakes import MarkingSanitizer, RecordingImageStorage

USER = UserId(UUID(int=1))


@dataclass
class _Scenario:
    """O use case com todas as portas em memória, para o teste olhar o estado de cada uma."""
    health_probability: float = 0.1
    used_today: int = 0
    plant: UserPlant = field(default_factory=lambda: make_user_plant(user_id=USER))
    uow: FakeHealthUnitOfWork = field(default_factory=FakeHealthUnitOfWork)
    analyzer: StubHealthAnalyzer = field(init=False)
    enricher: StubHealthEnricher = field(default_factory=StubHealthEnricher)
    storage: RecordingImageStorage = field(default_factory=RecordingImageStorage)
    users: FakeUserDirectory = field(default_factory=FakeUserDirectory)
    wallet: FakeTokenWallet = field(init=False)
    training: FakeTrainingRecorder = field(default_factory=FakeTrainingRecorder)

    def __post_init__(self) -> None:
        self.analyzer = StubHealthAnalyzer(make_assessment(self.health_probability))
        self.wallet = FakeTokenWallet(used_today=self.used_today)

    def use_case(self) -> DiagnoseHealthUseCase:
        return DiagnoseHealthUseCase(
            uow=self.uow,
            sanitizer=MarkingSanitizer(),
            health_analyzer=self.analyzer,
            enricher=self.enricher,
            storage=self.storage,
            users=self.users,
            wallet=self.wallet,
            training=self.training,
            plants=FakePlantLookup(self.plant),
        )

    def dto(self, user_plant_id: UserPlantId | None = None) -> DiagnoseHealthInputDTO:
        return DiagnoseHealthInputDTO(
            user_id=USER,
            user_plant_id=user_plant_id or self.plant.id,
            image_bytes=b"img",
            latitude=-27.5954,
            longitude=-48.548,
        )


async def test_unhealthy_plant_gets_the_gemini_analysis_and_pays_the_extra_token() -> None:
    # Arrange
    scenario = _Scenario(health_probability=0.1)

    # Act
    output = await scenario.use_case().execute(scenario.dto())

    # Assert
    record = output.record
    assert (record.vitality_score, record.source, record.treatment_plan) == (0.5, "kindwise+gemini", ("water less",))
    assert record.severity == HealthSeverity.MODERATE
    assert scenario.enricher.requests == [("Monstera deliciosa", ["leaf_spots"])]
    assert [cost for _, cost in scenario.wallet.charges] == [FeatureCost.DIAGNOSIS, FeatureCost.DIAGNOSIS_ENRICHMENT]
    assert scenario.uow.health_records.by_id == {record.id: record}
    assert scenario.uow.commits == 1


async def test_healthy_enough_plant_is_diagnosed_by_kindwise_alone() -> None:
    # Arrange: probabilidade de saúde a partir de 0.5 não aciona o Gemini
    scenario = _Scenario(health_probability=0.9)

    # Act
    output = await scenario.use_case().execute(scenario.dto())

    # Assert
    assert scenario.enricher.requests == []
    assert (output.record.vitality_score, output.record.source) == (0.9, "kindwise")
    assert output.record.is_healthy
    assert scenario.wallet.charged == 1


async def test_gemini_failure_degrades_to_kindwise_without_the_extra_token() -> None:
    # Arrange
    scenario = _Scenario()
    scenario.enricher.failure = ExternalServiceError(service="Gemini", retryable=True)

    # Act
    output = await scenario.use_case().execute(scenario.dto())

    # Assert
    record = output.record
    assert (record.vitality_score, record.treatment_plan, record.source) == (0.1, (), "kindwise")
    assert record.severity == HealthSeverity.CRITICAL
    assert scenario.wallet.charged == 1


async def test_diagnosis_records_an_anonymous_training_sample_linked_one_way() -> None:
    # Arrange
    scenario = _Scenario()

    # Act
    output = await scenario.use_case().execute(scenario.dto())

    # Assert: o diagnóstico aponta para a amostra; a amostra não tem dono, nem a foto do usuário
    (sample,) = scenario.training.health_samples
    assert output.record.training_sample_id == sample.id
    assert output.record.user_id == USER
    assert sample.image_key == "training/identifications/1.jpg"
    assert sample.image_key != output.record.image_key
    assert sample.reference_image_keys == ("species/references/1.jpg",)
    assert scenario.storage.rehosted == ["https://kindwise.test/ref.jpg"]
    assert sample.signals.diseases == (DiseaseSuggestion("leaf_spots", 0.8),)
    assert (sample.location.country, sample.location.state) == ("BR", "SP")
    assert (sample.location.grid_latitude, sample.location.grid_longitude) == (-27.6, -48.5)
    assert sample.period.day == 1


async def test_only_the_sanitized_image_leaves_the_app() -> None:
    # Arrange
    scenario = _Scenario()

    # Act
    await scenario.use_case().execute(scenario.dto())

    # Assert
    assert scenario.analyzer.received == [b"clean:img"]
    assert scenario.storage.user_uploads == [b"clean:img"]
    assert scenario.storage.training_uploads == [b"clean:img"]


async def test_response_keeps_the_provider_reference_images() -> None:
    # Arrange
    scenario = _Scenario()

    # Act
    output = await scenario.use_case().execute(scenario.dto())

    # Assert
    assert output.similar_images_urls == ("https://kindwise.test/ref.jpg",)


async def test_diagnosis_without_tokens_is_refused_before_calling_providers() -> None:
    # Arrange: antes o /diagnose não conferia o saldo e gastava créditos dos provedores
    scenario = _Scenario(used_today=3)

    # Act & Assert
    with pytest.raises(DailyQuotaExceededError):
        await scenario.use_case().execute(scenario.dto())
    assert (scenario.analyzer.received, scenario.enricher.requests, scenario.storage.user_uploads) == ([], [], [])
    assert scenario.training.is_empty


async def test_last_token_buys_the_diagnosis_without_gemini() -> None:
    # Arrange: sobra 1 token; o complemento custaria mais 1
    scenario = _Scenario(used_today=2)

    # Act
    output = await scenario.use_case().execute(scenario.dto())

    # Assert
    assert scenario.enricher.requests == []
    assert output.record.source == "kindwise"
    assert scenario.wallet.used_today == 3


async def test_plant_of_another_user_is_not_found_and_costs_nothing() -> None:
    # Arrange
    scenario = _Scenario(plant=make_user_plant(user_id=UserId(uuid4())))

    # Act & Assert
    with pytest.raises(PlantNotFoundError):
        await scenario.use_case().execute(scenario.dto(user_plant_id=scenario.plant.id))
    assert scenario.analyzer.received == []
    assert scenario.wallet.charges == []


async def test_missing_account_is_not_found() -> None:
    # Arrange
    scenario = _Scenario()
    scenario.users.missing.add(USER)

    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await scenario.use_case().execute(scenario.dto())
    assert scenario.analyzer.received == []
