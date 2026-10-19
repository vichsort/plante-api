"""
Comportamento do Postgres que o SQLite não reproduzia: fuso horário, enums nativos, unicidade e
ações das FKs. O schema vem das migrations (fixture `postgres_url`), então os testes conferem o
banco real, não o metadata dos modelos.
"""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.models import metadata
from src.modules.catalog.adapters.persistence.repositories.plant_species import (
    PlantSpeciesRepository,
)
from src.modules.garden.adapters.persistence.repositories.user_plant import (
    UserPlantRepository,
)
from src.modules.garden.domain.value_objects.streak import Streak
from src.modules.health.adapters.persistence.repositories.health_record import (
    HealthRecordRepository,
)
from src.modules.identity.adapters.persistence.repositories.user import UserRepository
from src.modules.training import (
    FeedbackOrigin,
    FeedbackVerdict,
    HealthLabel,
    IdentificationLabel,
    TrainingFeedback,
)
from src.modules.training.adapters.persistence.repositories.training import (
    TrainingRepository,
)
from tests.factories import (
    MONTH,
    make_care_schedule,
    make_health_record,
    make_species,
    make_user,
    make_user_plant,
)
from tests.integration.persistence.seed import (
    seed_identification,
    seed_training_health_sample,
)

_BRT = timezone(timedelta(hours=-3))


async def _scalar_count(session: AsyncSession, table: str, column: str, value: UUID) -> int:
    result = await session.execute(text(f"SELECT count(*) FROM {table} WHERE {column} = :v"), {"v": value})
    return int(result.scalar_one())


# --- Fuso horário ----------------------------------------------------------------------------

async def test_no_column_is_timestamp_without_time_zone(db_session: AsyncSession) -> None:
    result = await db_session.execute(text(
        "SELECT table_name || '.' || column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND data_type = 'timestamp without time zone' "
        "AND table_name <> 'alembic_version'"
    ))
    assert result.scalars().all() == []


async def test_datetime_keeps_instant_regardless_of_session_time_zone(db_session: AsyncSession) -> None:
    await db_session.execute(text("SET LOCAL TIME ZONE 'Asia/Tokyo'"))
    user = await UserRepository(db_session).save(make_user(email="tz@plante.org"))
    identification = await seed_identification(db_session, user.id)
    added_at = datetime(2026, 10, 15, 21, 30, tzinfo=_BRT)  # 00:30 UTC do dia seguinte
    due_on = date(2026, 10, 22)
    plant = make_user_plant(
        user_id=user.id, identification_id=identification.id, care_schedule=make_care_schedule(next_due_on=due_on)
    )
    plant = replace(plant, added_at=added_at)
    repo = UserPlantRepository(db_session)
    await repo.save(plant)
    await db_session.commit()
    db_session.expire_all()

    loaded = await repo.get_by_id(plant.id)

    assert loaded is not None
    assert loaded.added_at == added_at
    assert loaded.added_at.utcoffset() is not None
    assert loaded.care_schedule.next_due_on == due_on  # dia local: o fuso da sessão não o desloca


async def test_streak_query_selects_by_local_due_day(db_session: AsyncSession) -> None:
    # Arrange
    user = await UserRepository(db_session).save(make_user(email="overdue@plante.org"))
    repo = UserPlantRepository(db_session)
    due_on = date(2026, 10, 15)
    plants = {}
    for name, streak in (("with_streak", 3), ("without_streak", 0)):
        identification = await seed_identification(db_session, user.id)
        plant = make_user_plant(
            user_id=user.id, identification_id=identification.id, care_schedule=make_care_schedule(next_due_on=due_on)
        )
        plant.watering_streak = Streak(current_count=streak)
        plants[name] = await repo.save(plant)
    await db_session.commit()

    # Act
    on_due_day = [p.id for p in await repo.list_with_streak_due_before(due_on)]
    day_after = [p.id for p in await repo.list_with_streak_due_before(due_on + timedelta(days=1))]

    # Assert
    assert plants["with_streak"].id not in on_due_day
    assert plants["with_streak"].id in day_after
    assert plants["without_streak"].id not in day_after  # sem sequência não há o que quebrar


# --- Enums nativos ---------------------------------------------------------------------------

def _model_enums() -> dict[str, list[str]]:
    enums: dict[str, list[str]] = {}
    for table in metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, SAEnum) and column.type.name:
                enums[column.type.name] = list(column.type.enums)
    return enums


async def test_postgres_enum_types_match_models(db_session: AsyncSession) -> None:
    result = await db_session.execute(text(
        "SELECT t.typname, e.enumlabel FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid "
        "ORDER BY t.typname, e.enumsortorder"
    ))
    in_database: dict[str, list[str]] = {}
    for name, label in result.tuples():
        in_database.setdefault(name, []).append(label)

    # Valor novo num enum do Python exige migration (`ALTER TYPE ... ADD VALUE`)
    assert {name: sorted(labels) for name, labels in in_database.items()} == {
        name: sorted(labels) for name, labels in _model_enums().items()
    }


async def test_enum_column_rejects_unknown_value(db_session: AsyncSession) -> None:
    user = await UserRepository(db_session).save(make_user(email="enum@plante.org"))

    with pytest.raises(DBAPIError, match="invalid input value for enum"):
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    "INSERT INTO subscriptions (user_id, tier, tokens_used_today, created_at, updated_at)"
                    " VALUES (:id, 'GOLD', 0, now(), now())"
                ),
                {"id": user.id},
            )


# --- Unicidade -------------------------------------------------------------------------------

async def test_duplicate_email_violates_unique_constraint(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    await repo.save(make_user(email="dup@plante.org"))

    with pytest.raises(IntegrityError, match="ix_users_email|unique"):
        async with db_session.begin_nested():
            await repo.save(make_user(email="dup@plante.org"))


async def test_email_is_stored_normalized_and_unique_regardless_of_case(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    await repo.save(make_user(email=" Case@Plante.org "))

    assert await repo.get_by_email("case@plante.org") is not None
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await repo.save(make_user(email="CASE@plante.org"))


async def test_check_constraint_rejects_non_normalized_email(db_session: AsyncSession) -> None:
    user = await UserRepository(db_session).save(make_user(email="check@plante.org"))

    with pytest.raises(IntegrityError, match="ck_users_email_normalized"):
        async with db_session.begin_nested():
            await db_session.execute(
                text("UPDATE users SET email = 'Check@Plante.org' WHERE id = :id"), {"id": user.id}
            )


async def test_duplicate_species_scientific_name_violates_unique_constraint(db_session: AsyncSession) -> None:
    repo = PlantSpeciesRepository(db_session)
    await repo.save(make_species("Ficus lyrata"))

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await repo.save(make_species("Ficus lyrata"))


async def test_training_sample_belongs_to_at_most_one_user_record(db_session: AsyncSession) -> None:
    user = await UserRepository(db_session).save(make_user(email="sample@plante.org"))
    identification = await seed_identification(db_session, user.id)
    plant = await UserPlantRepository(db_session).save(make_user_plant(user_id=user.id, identification_id=identification.id))
    training = await seed_training_health_sample(db_session)
    records = HealthRecordRepository(db_session)
    await records.save(make_health_record(user_id=user.id, user_plant_id=plant.id, training_sample_id=training.id))

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await records.save(make_health_record(user_id=user.id, user_plant_id=plant.id, training_sample_id=training.id))


async def test_feedback_targets_exactly_one_sample(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="ck_training_feedback_one_target"):
        async with db_session.begin_nested():
            await db_session.execute(text(
                "INSERT INTO training_feedback (id, verdict, origin, given_on) "
                "VALUES (gen_random_uuid(), 'correct', 'explicit', CURRENT_DATE)"
            ))


# --- Chaves estrangeiras ---------------------------------------------------------------------

# (tabela, coluna) -> (tabela referenciada, ação no DELETE). Mudar uma linha daqui exige
# migration e uma decisão consciente; os efeitos problemáticos estão nos testes abaixo e no todo.
_EXPECTED_FOREIGN_KEYS = {
    # Lado do usuário: tudo sai com o usuário (CASCADE)
    ("identifications", "user_id"): ("users", "CASCADE"),
    ("identifications", "species_id"): ("plant_species", "RESTRICT"),
    ("user_plants", "user_id"): ("users", "CASCADE"),
    ("user_plants", "identification_id"): ("identifications", "CASCADE"),
    ("health_records", "user_id"): ("users", "CASCADE"),
    ("health_records", "user_plant_id"): ("user_plants", "CASCADE"),
    ("user_achievements", "user_id"): ("users", "CASCADE"),
    ("subscriptions", "user_id"): ("users", "CASCADE"),
    ("plant_reference_images", "user_id"): ("users", "SET NULL"),
    # Vínculos de mão única para o treino: o lado do usuário aponta para a amostra, nunca o contrário
    ("identifications", "training_sample_id"): ("training_identification_samples", "RESTRICT"),
    ("health_records", "training_sample_id"): ("training_health_samples", "RESTRICT"),
    # Dentro do treino
    ("training_feedback", "identification_sample_id"): ("training_identification_samples", "RESTRICT"),
    ("training_feedback", "health_sample_id"): ("training_health_samples", "RESTRICT"),
}

_DELETE_ACTIONS = {"a": "NO ACTION", "r": "RESTRICT", "c": "CASCADE", "n": "SET NULL", "d": "SET DEFAULT"}


async def test_foreign_keys_and_delete_actions(db_session: AsyncSession) -> None:
    result = await db_session.execute(text(
        "SELECT src.relname, att.attname, ref.relname, con.confdeltype "
        "FROM pg_constraint con "
        "JOIN pg_class src ON src.oid = con.conrelid "
        "JOIN pg_class ref ON ref.oid = con.confrelid "
        "JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey) "
        "JOIN pg_namespace ns ON ns.oid = src.relnamespace "
        "WHERE con.contype = 'f' AND ns.nspname = 'public'"
    ))
    in_database = {
        (table, column): (referenced, _DELETE_ACTIONS[action])
        for table, column, referenced, action in result.tuples()
    }

    assert in_database == _EXPECTED_FOREIGN_KEYS


async def _user_with_everything(session: AsyncSession, email: str) -> dict[str, UUID]:
    """Usuário com identificação, planta, diagnóstico e feedback nas duas amostras de treino."""
    user = await UserRepository(session).save(make_user(email=email))
    identification = await seed_identification(session, user.id)
    plant = await UserPlantRepository(session).save(make_user_plant(user_id=user.id, identification_id=identification.id))
    health_training = await seed_training_health_sample(session)
    record = await HealthRecordRepository(session).save(
        make_health_record(user_id=user.id, user_plant_id=plant.id, training_sample_id=health_training.id)
    )
    training = TrainingRepository(session)
    await training.add_feedback(TrainingFeedback.create(
        IdentificationLabel(identification.training_sample_id), FeedbackVerdict.CORRECT, FeedbackOrigin.EXPLICIT, MONTH,
    ))
    await training.add_feedback(TrainingFeedback.create(
        HealthLabel(health_training.id), FeedbackVerdict.WRONG, FeedbackOrigin.EXPLICIT, MONTH,
    ))
    await session.commit()
    return {
        "user": user.id,
        "identification": identification.id,
        "plant": plant.id,
        "record": record.id,
        "identification_training": identification.training_sample_id,
        "health_training": health_training.id,
    }


async def _training_rows(session: AsyncSession, ids: dict[str, UUID]) -> tuple[int, int, int]:
    return (
        await _scalar_count(session, "training_identification_samples", "id", ids["identification_training"]),
        await _scalar_count(session, "training_health_samples", "id", ids["health_training"]),
        await _scalar_count(session, "training_feedback", "identification_sample_id", ids["identification_training"])
        + await _scalar_count(session, "training_feedback", "health_sample_id", ids["health_training"]),
    )


async def test_deleting_user_removes_personal_data_and_keeps_training_data(db_session: AsyncSession) -> None:
    """
    Antes do plano C, apagar um usuário com amostra de saúde falhava (SET NULL × CASCADE na mesma
    linha). Agora o lado do usuário sai inteiro e o dataset de treino fica intacto.
    """
    ids = await _user_with_everything(db_session, "delete-me@plante.org")

    await db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": ids["user"]})

    assert await _scalar_count(db_session, "identifications", "id", ids["identification"]) == 0
    assert await _scalar_count(db_session, "user_plants", "id", ids["plant"]) == 0
    assert await _scalar_count(db_session, "health_records", "id", ids["record"]) == 0
    assert await _training_rows(db_session, ids) == (1, 1, 2)


async def test_deleting_plant_keeps_identification_and_training_data(db_session: AsyncSession) -> None:
    ids = await _user_with_everything(db_session, "plant-gone@plante.org")

    await db_session.execute(text("DELETE FROM user_plants WHERE id = :id"), {"id": ids["plant"]})

    assert await _scalar_count(db_session, "health_records", "id", ids["record"]) == 0
    assert await _scalar_count(db_session, "identifications", "id", ids["identification"]) == 1
    assert await _training_rows(db_session, ids) == (1, 1, 2)
