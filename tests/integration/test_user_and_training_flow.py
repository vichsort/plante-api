"""
Fluxo completo contra o Postgres real (use cases + Unit of Work reais; IA, S3 e eventos falsos):
identificar → feedback → adicionar ao jardim → regar → diagnosticar → feedback → apagar planta →
apagar usuário. No fim, o lado do usuário sumiu e o dataset de treino continua inteiro, sem
nada que aponte para ele.
"""
from unittest.mock import AsyncMock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.catalog.adapters.persistence.unit_of_work import (
    SqlAlchemyCatalogUnitOfWork,
)
from src.modules.catalog.domain.services.species_registry import SpeciesRegistry
from src.modules.garden.adapters.persistence.unit_of_work import (
    SqlAlchemyGardenUnitOfWork,
)
from src.modules.garden.domain.services.plant_lookup import PlantLookup
from src.modules.garden.domain.use_cases.add_plant import (
    AddPlantToGardenInputDTO,
    AddPlantToGardenUseCase,
)
from src.modules.garden.domain.use_cases.delete_plant import (
    DeleteUserPlantInputDTO,
    DeleteUserPlantUseCase,
)
from src.modules.garden.domain.use_cases.water_plant import (
    WaterPlantInputDTO,
    WaterPlantUseCase,
)
from src.modules.health.adapters.persistence.unit_of_work import (
    SqlAlchemyHealthUnitOfWork,
)
from src.modules.health.domain.ports.health_analyzer import (
    DiseaseHint,
    HealthAssessmentResult,
)
from src.modules.health.domain.use_cases.diagnose import (
    DiagnoseHealthInputDTO,
    DiagnoseHealthUseCase,
)
from src.modules.health.domain.use_cases.give_feedback import (
    GiveHealthFeedbackInputDTO,
    GiveHealthFeedbackUseCase,
)
from src.modules.identification.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentificationUnitOfWork,
)
from src.modules.identification.domain.ports.plant_identifier import (
    IdentificationResult,
)
from src.modules.identification.domain.services.identification_lookup import (
    IdentificationLookup,
)
from src.modules.identification.domain.use_cases.give_feedback import (
    GiveIdentificationFeedbackInputDTO,
    GiveIdentificationFeedbackUseCase,
)
from src.modules.identification.domain.use_cases.identify_plant import (
    IdentifyPlantInputDTO,
    IdentifyPlantUseCase,
)
from src.modules.identification.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from src.modules.identity.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentityUnitOfWork,
)
from src.modules.identity.domain.services.user_directory import UserDirectory
from src.modules.subscription.adapters.persistence.unit_of_work import (
    SqlAlchemySubscriptionUnitOfWork,
)
from src.modules.subscription.domain.services.garden_quota import GardenQuota
from src.modules.subscription.domain.services.token_wallet import TokenWallet
from src.modules.training import (
    DiseaseSuggestion,
    FeedbackOrigin,
    FeedbackVerdict,
    HealthSignals,
)
from src.modules.training.adapters.persistence.unit_of_work import (
    SqlAlchemyTrainingUnitOfWork,
)
from src.modules.training.domain.services.recorder import TrainingRecorder
from src.shared.tests.fakes import MarkingSanitizer
from tests.factories import CALENDAR, make_identification_signals, make_user


def _storage() -> AsyncMock:
    storage = AsyncMock()
    storage.upload_identification_image.side_effect = ["identifications/user-1.jpg", "identifications/user-2.jpg"]
    storage.upload_training_image.side_effect = ["training/identifications/a.jpg", "training/identifications/b.jpg"]
    storage.download_and_rehost.return_value = "species/references/ref.jpg"
    return storage


def _identifier() -> AsyncMock:
    identifier = AsyncMock()
    identifier.identify.return_value = IdentificationResult(
        scientific_name="Monstera deliciosa",
        confidence=ConfidenceScore(0.9),
        source="consensus",
        family="Araceae",
        genus="Monstera",
        signals=make_identification_signals(),
    )
    return identifier


def _analyzer() -> AsyncMock:
    analyzer = AsyncMock()
    analyzer.assess_health.return_value = HealthAssessmentResult(
        is_healthy=False,
        health_probability=0.3,
        diseases=(DiseaseHint("leaf_spots", 0.8, ("https://kindwise/ref.jpg",)),),
        signals=HealthSignals(provider="kindwise", is_healthy_probability=0.3, diseases=(DiseaseSuggestion("leaf_spots", 0.8),)),
    )
    return analyzer


async def _rows(session: AsyncSession, table: str) -> list[str]:
    result = await session.execute(text(f"SELECT CAST(t AS text) FROM {table} t"))
    return list(result.scalars().all())


async def test_full_flow_keeps_training_data_anonymous_after_user_is_deleted(
    session_factory: async_sessionmaker[AsyncSession],
    db_session: AsyncSession,
) -> None:
    def health() -> SqlAlchemyHealthUnitOfWork:
        return SqlAlchemyHealthUnitOfWork(session_factory)

    def garden() -> SqlAlchemyGardenUnitOfWork:
        return SqlAlchemyGardenUnitOfWork(session_factory)

    def identifications() -> SqlAlchemyIdentificationUnitOfWork:
        return SqlAlchemyIdentificationUnitOfWork(session_factory)

    def training() -> TrainingRecorder:
        return TrainingRecorder(SqlAlchemyTrainingUnitOfWork(session_factory))

    def wallet() -> TokenWallet:
        return TokenWallet(SqlAlchemySubscriptionUnitOfWork(session_factory), CALENDAR)

    async with SqlAlchemyIdentityUnitOfWork(session_factory) as setup:
        user = await setup.users.save(make_user(email="flow@plante.org"))
        await setup.commit()
    users = UserDirectory(SqlAlchemyIdentityUnitOfWork(session_factory))

    storage = _storage()
    enricher = AsyncMock()
    enricher.diagnose_health.return_value = None  # sem análise complementar

    # 1. Identificar (com GPS) e dar feedback
    identified = await IdentifyPlantUseCase(
        uow=identifications(), sanitizer=MarkingSanitizer(), plant_identifier=_identifier(), storage=storage, publisher=AsyncMock(),
        users=users, wallet=wallet(), training=training(), catalog=SpeciesRegistry(SqlAlchemyCatalogUnitOfWork(session_factory)),
    ).execute(IdentifyPlantInputDTO(user_id=user.id, image_bytes=b"photo", latitude=-23.5617, longitude=-46.6559))

    await GiveIdentificationFeedbackUseCase(uow=identifications(), training=training()).execute(GiveIdentificationFeedbackInputDTO(
        user_id=user.id, identification_id=identified.identification_id,
        verdict=FeedbackVerdict.WRONG, suggested_name="Monstera adansonii",
    ))

    # 2. Adicionar ao jardim (sinal implícito) e regar
    quota = GardenQuota(SqlAlchemySubscriptionUnitOfWork(session_factory))
    plant = (await AddPlantToGardenUseCase(
        uow=garden(), publisher=AsyncMock(), calendar=CALENDAR, users=users, quota=quota, training=training(),
        identifications=IdentificationLookup(identifications()),
    ).execute(
        AddPlantToGardenInputDTO(user_id=user.id, identification_id=identified.identification_id)
    )).plant
    await WaterPlantUseCase(uow=garden(), publisher=AsyncMock(), calendar=CALENDAR).execute(
        WaterPlantInputDTO(user_id=user.id, user_plant_id=plant.id)
    )

    # 3. Diagnosticar e dar feedback
    diagnosis = await DiagnoseHealthUseCase(
        uow=health(), sanitizer=MarkingSanitizer(), health_analyzer=_analyzer(), enricher=enricher, storage=storage,
        users=users, wallet=wallet(), training=training(), plants=PlantLookup(garden()),
    ).execute(DiagnoseHealthInputDTO(user_id=user.id, user_plant_id=plant.id, image_bytes=b"leaf"))

    await GiveHealthFeedbackUseCase(uow=health(), training=training()).execute(GiveHealthFeedbackInputDTO(
        user_id=user.id, health_record_id=diagnosis.record.id, verdict=FeedbackVerdict.CORRECT,
    ))

    identification = await IdentificationLookup(identifications()).get_for_user(identified.identification_id, user.id)
    async with SqlAlchemyTrainingUnitOfWork(session_factory) as dataset:
        feedback = await dataset.training.list_feedback(identification.training_sample_id)
        assert {(f.verdict, f.origin) for f in feedback} == {
            (FeedbackVerdict.WRONG, FeedbackOrigin.EXPLICIT),
            (FeedbackVerdict.CORRECT, FeedbackOrigin.ADDED_TO_GARDEN),
        }
        sample = await dataset.training.get_identification_sample(identification.training_sample_id)
        assert sample is not None
        assert (sample.location.grid_latitude, sample.location.grid_longitude) == (-23.6, -46.7)

    # 4. Apagar a planta (soft delete) e depois o usuário (hard delete, como uma exclusão de conta)
    await DeleteUserPlantUseCase(uow=garden()).execute(DeleteUserPlantInputDTO(user_id=user.id, user_plant_id=plant.id))
    await db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})

    for table in ("identifications", "user_plants", "health_records", "subscriptions"):
        assert await _rows(db_session, table) == [], f"{table} deveria ter saído com o usuário"

    training_rows = {
        table: await _rows(db_session, table)
        for table in ("training_identification_samples", "training_health_samples", "training_feedback")
    }
    assert {table: len(rows) for table, rows in training_rows.items()} == {
        "training_identification_samples": 1,
        "training_health_samples": 1,
        "training_feedback": 3,
    }
    # Nada no dataset aponta para o usuário: nem o ID, nem as fotos dele, nem o GPS exato
    everything = "\n".join(row for rows in training_rows.values() for row in rows)
    for personal in (str(user.id), "identifications/user-1.jpg", "identifications/user-2.jpg", "-23.5617", "-46.6559"):
        assert personal not in everything
