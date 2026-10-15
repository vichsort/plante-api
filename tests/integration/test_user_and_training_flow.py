"""
Fluxo completo contra o Postgres real (use cases + Unit of Work reais; IA, S3 e eventos falsos):
identificar → feedback → adicionar ao jardim → regar → diagnosticar → feedback → apagar planta →
apagar usuário. No fim, o lado do usuário sumiu e o dataset de treino continua inteiro, sem
nada que aponte para ele.
"""
from unittest.mock import AsyncMock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.domain.entities.training import FeedbackOrigin, FeedbackVerdict
from src.domain.ports.health_analyzer import DiseaseHint, HealthAssessmentResult
from src.domain.ports.plant_identifier import IdentificationResult
from src.domain.use_cases.add_plant_to_garden_use_case import (
    AddPlantToGardenInputDTO,
    AddPlantToGardenUseCase,
)
from src.domain.use_cases.delete_user_plant_use_case import (
    DeleteUserPlantInputDTO,
    DeleteUserPlantUseCase,
)
from src.domain.use_cases.diagnose_health_use_case import (
    DiagnoseHealthInputDTO,
    DiagnoseHealthUseCase,
)
from src.domain.use_cases.give_health_feedback_use_case import (
    GiveHealthFeedbackInputDTO,
    GiveHealthFeedbackUseCase,
)
from src.domain.use_cases.give_identification_feedback_use_case import (
    GiveIdentificationFeedbackInputDTO,
    GiveIdentificationFeedbackUseCase,
)
from src.domain.use_cases.identify_plant_use_case import (
    IdentifyPlantInputDTO,
    IdentifyPlantUseCase,
)
from src.domain.use_cases.water_plant_use_case import (
    WaterPlantInputDTO,
    WaterPlantUseCase,
)
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.provider_signals import DiseaseSuggestion, HealthSignals
from tests.factories import make_identification_signals, make_user
from tests.fakes import MarkingSanitizer


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
    def uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    async with uow() as setup:
        user = await setup.users.save(make_user(email="flow@plante.org"))
        await setup.commit()

    storage = _storage()
    enricher = AsyncMock()
    enricher.diagnose_health.return_value = None  # sem análise complementar

    # 1. Identificar (com GPS) e dar feedback
    identified = await IdentifyPlantUseCase(
        uow=uow(), sanitizer=MarkingSanitizer(), plant_identifier=_identifier(), storage=storage, publisher=AsyncMock(),
    ).execute(IdentifyPlantInputDTO(user_id=user.id, image_bytes=b"photo", latitude=-23.5617, longitude=-46.6559))

    await GiveIdentificationFeedbackUseCase(uow=uow()).execute(GiveIdentificationFeedbackInputDTO(
        user_id=user.id, identification_id=identified.identification_id,
        verdict=FeedbackVerdict.WRONG, suggested_name="Monstera adansonii",
    ))

    # 2. Adicionar ao jardim (sinal implícito) e regar
    plant = await AddPlantToGardenUseCase(uow=uow(), publisher=AsyncMock()).execute(
        AddPlantToGardenInputDTO(user_id=user.id, identification_id=identified.identification_id)
    )
    await WaterPlantUseCase(uow=uow(), publisher=AsyncMock()).execute(
        WaterPlantInputDTO(user_id=user.id, user_plant_id=plant.id)
    )

    # 3. Diagnosticar e dar feedback
    diagnosis = await DiagnoseHealthUseCase(
        uow=uow(), sanitizer=MarkingSanitizer(), health_analyzer=_analyzer(), plant_enricher=enricher, storage=storage,
    ).execute(DiagnoseHealthInputDTO(user_id=user.id, user_plant_id=plant.id, image_bytes=b"leaf"))

    await GiveHealthFeedbackUseCase(uow=uow()).execute(GiveHealthFeedbackInputDTO(
        user_id=user.id, health_record_id=diagnosis.record.id, verdict=FeedbackVerdict.CORRECT,
    ))

    async with uow() as check:
        identification = await check.identifications.get_for_user(identified.identification_id, user.id)
        assert identification is not None
        feedback = await check.training.list_feedback(identification.training_sample_id)
        assert {(f.verdict, f.origin) for f in feedback} == {
            (FeedbackVerdict.WRONG, FeedbackOrigin.EXPLICIT),
            (FeedbackVerdict.CORRECT, FeedbackOrigin.ADDED_TO_GARDEN),
        }
        sample = await check.training.get_identification_sample(identification.training_sample_id)
        assert sample is not None
        assert (sample.location.grid_latitude, sample.location.grid_longitude) == (-23.6, -46.7)

    # 4. Apagar a planta (soft delete) e depois o usuário (hard delete, como uma exclusão de conta)
    await DeleteUserPlantUseCase(uow=uow()).execute(DeleteUserPlantInputDTO(user_id=user.id, user_plant_id=plant.id))
    await db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})

    for table in ("identifications", "user_plants", "health_records"):
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
