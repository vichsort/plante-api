"""
Comportamento do Postgres que o SQLite não reproduzia: fuso horário, enums nativos, unicidade e
ações das FKs. O schema vem das migrations (fixture `postgres_url`), então os testes conferem o
banco real, não o metadata dos modelos.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.models import Base
from src.adapters.persistence.repositories.health_identification_sample_repository import (
    HealthIdentificationSampleRepository,
)
from src.adapters.persistence.repositories.health_record_repository import (
    HealthRecordRepository,
)
from src.adapters.persistence.repositories.identification_sample_repository import (
    IdentificationSampleRepository,
)
from src.adapters.persistence.repositories.plant_species_repository import (
    PlantSpeciesRepository,
)
from src.adapters.persistence.repositories.user_plant_repository import (
    UserPlantRepository,
)
from src.adapters.persistence.repositories.user_repository import UserRepository
from src.domain.value_objects.ids import (
    HealthRecordId,
    HealthSampleId,
    UserId,
    UserPlantId,
)
from tests.factories import (
    make_care_schedule,
    make_health_record,
    make_health_sample,
    make_identification_sample,
    make_species,
    make_user,
    make_user_plant,
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
    added_at = datetime(2026, 10, 15, 21, 30, tzinfo=_BRT)  # 00:30 UTC do dia seguinte
    due_at = datetime(2026, 10, 22, 9, 0, tzinfo=_BRT)
    plant = make_user_plant(user_id=user.id, care_schedule=make_care_schedule(next_due_at=due_at))
    plant = replace(plant, added_at=added_at)
    repo = UserPlantRepository(db_session)
    await repo.save(plant)
    await db_session.commit()
    db_session.expire_all()

    loaded = await repo.get_by_id(plant.id)

    assert loaded is not None
    assert loaded.added_at == added_at
    assert loaded.added_at.utcoffset() is not None
    assert loaded.care_schedule.next_due_at == due_at


async def test_overdue_query_compares_instants_across_offsets(db_session: AsyncSession) -> None:
    user = await UserRepository(db_session).save(make_user(email="overdue@plante.org"))
    due_at = datetime(2026, 10, 15, 9, 0, tzinfo=_BRT)  # 12:00 UTC
    plant = make_user_plant(user_id=user.id, care_schedule=make_care_schedule(next_due_at=due_at))
    repo = UserPlantRepository(db_session)
    await repo.save(plant)
    await db_session.commit()

    # Mesmo instante em outro fuso: 11:59 UTC ainda não venceu; 12:01 UTC já venceu
    before = datetime(2026, 10, 15, 20, 59, tzinfo=timezone(timedelta(hours=9)))
    after = datetime(2026, 10, 15, 21, 1, tzinfo=timezone(timedelta(hours=9)))

    assert plant.id not in [p.id for p in await repo.get_overdue_plants(before)]
    assert plant.id in [p.id for p in await repo.get_overdue_plants(after)]


# --- Enums nativos ---------------------------------------------------------------------------

def _model_enums() -> dict[str, list[str]]:
    enums: dict[str, list[str]] = {}
    for table in Base.metadata.tables.values():
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
                text('UPDATE users SET subscription = \'GOLD\' WHERE id = :id'), {"id": user.id}
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


async def test_health_record_has_at_most_one_sample(db_session: AsyncSession) -> None:
    user = await UserRepository(db_session).save(make_user(email="sample@plante.org"))
    plant = await UserPlantRepository(db_session).save(make_user_plant(user_id=user.id))
    record = await HealthRecordRepository(db_session).save(
        make_health_record(user_id=user.id, user_plant_id=plant.id)
    )
    samples = HealthIdentificationSampleRepository(db_session)
    await samples.save(make_health_sample(record))

    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await samples.save(make_health_sample(record))


# --- Chaves estrangeiras ---------------------------------------------------------------------

# (tabela, coluna) -> (tabela referenciada, ação no DELETE). Mudar uma linha daqui exige
# migration e uma decisão consciente; os efeitos problemáticos estão nos testes abaixo e no todo.
_EXPECTED_FOREIGN_KEYS = {
    ("health_identification_samples", "health_record_id"): ("health_records", "CASCADE"),
    ("health_identification_samples", "user_id"): ("users", "SET NULL"),
    ("health_records", "user_id"): ("users", "SET NULL"),
    ("health_records", "user_plant_id"): ("user_plants", "CASCADE"),
    ("plant_identification_samples", "species_id"): ("plant_species", "CASCADE"),
    ("plant_identification_samples", "user_id"): ("users", "SET NULL"),
    ("plant_reference_images", "user_id"): ("users", "SET NULL"),
    ("user_achievements", "user_id"): ("users", "CASCADE"),
    ("user_plants", "user_id"): ("users", "CASCADE"),
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


async def _plant_with_health_sample(session: AsyncSession, email: str) -> tuple[UserId, UserPlantId, HealthRecordId, HealthSampleId]:
    user = await UserRepository(session).save(make_user(email=email))
    plant = await UserPlantRepository(session).save(make_user_plant(user_id=user.id))
    record = await HealthRecordRepository(session).save(
        make_health_record(user_id=user.id, user_plant_id=plant.id)
    )
    sample = await HealthIdentificationSampleRepository(session).save(make_health_sample(record))
    await session.commit()
    return user.id, plant.id, record.id, sample.id


async def test_deleting_user_plant_cascades_to_health_samples(db_session: AsyncSession) -> None:
    """
    Documenta o comportamento atual (ver todo): apagar a planta de verdade apaga os diagnósticos
    e as amostras de saúde, que são dataset de treino. Hoje a exclusão é soft delete.
    """
    _, plant_id, record_id, sample_id = await _plant_with_health_sample(db_session, "plant-cascade@plante.org")

    await db_session.execute(text("DELETE FROM user_plants WHERE id = :id"), {"id": plant_id})

    assert await _scalar_count(db_session, "health_records", "id", record_id) == 0
    assert await _scalar_count(db_session, "health_identification_samples", "id", sample_id) == 0


async def test_deleting_user_with_health_sample_fails(db_session: AsyncSession) -> None:
    """
    Documenta o comportamento atual (ver todo): a amostra recebe SET NULL em `user_id` e perde o
    diagnóstico pela cascata users -> user_plants -> health_records no mesmo DELETE; o UPDATE
    do SET NULL viola a FK `health_record_id` e o usuário não pode ser apagado.
    """
    user_id, _, _, _ = await _plant_with_health_sample(db_session, "user-cascade@plante.org")

    with pytest.raises(IntegrityError, match="health_identification_samples_health_record_id_fkey"):
        async with db_session.begin_nested():
            await db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


async def test_deleting_user_keeps_identification_samples_anonymized(db_session: AsyncSession) -> None:
    user = await UserRepository(db_session).save(make_user(email="anon@plante.org"))
    plant = await UserPlantRepository(db_session).save(make_user_plant(user_id=user.id))
    species = await PlantSpeciesRepository(db_session).save(make_species("Pilea peperomioides"))
    identification = replace(make_identification_sample(user_id=user.id), species_id=species.id)
    await IdentificationSampleRepository(db_session).save(identification)
    await db_session.commit()

    await db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})

    assert await _scalar_count(db_session, "user_plants", "id", plant.id) == 0
    kept = await db_session.execute(
        text("SELECT user_id FROM plant_identification_samples WHERE id = :id"), {"id": identification.id}
    )
    assert kept.scalar_one() is None
