"""
Guarda do anonimato do dataset de treino, conferida no banco criado pelas migrations.

Quem acrescentar uma coluna a uma tabela de treino precisa passar por aqui: a lista é fechada
de propósito. Antes de liberar uma coluna nova, confira se ela não identifica ninguém (ID ou
dado do usuário, GPS exato, URL ou chave da foto do usuário, horário exato).
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_LOCATION = {"period", "country", "state", "grid_latitude", "grid_longitude"}

_ALLOWED_COLUMNS = {
    "training_identification_samples": {
        "id", "image_key", "scientific_name", "family", "genus", "gbif_id", "provider_entity_id",
        "source", "confidence", "low_confidence", "signals", *_LOCATION,
    },
    "training_health_samples": {
        "id", "image_key", "scientific_name", "vitality_score", "severity", "source",
        "issues_detected", "treatment_plan", "reference_image_keys", "recovery_estimate_days",
        "notes", "signals", *_LOCATION,
    },
    "training_feedback": {
        "id", "identification_sample_id", "health_sample_id", "verdict", "origin",
        "suggested_name", "given_on",
    },
}


async def test_training_tables_have_only_allowed_columns(db_session: AsyncSession) -> None:
    result = await db_session.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name LIKE 'training\\_%'"
    ))
    columns: dict[str, set[str]] = {}
    for table, column in result.tuples():
        columns.setdefault(table, set()).add(column)

    assert columns == _ALLOWED_COLUMNS


async def test_training_tables_only_reference_training_tables(db_session: AsyncSession) -> None:
    result = await db_session.execute(text(
        "SELECT src.relname, ref.relname FROM pg_constraint con "
        "JOIN pg_class src ON src.oid = con.conrelid "
        "JOIN pg_class ref ON ref.oid = con.confrelid "
        "WHERE con.contype = 'f' AND src.relname LIKE 'training\\_%'"
    ))

    for source, referenced in result.tuples():
        assert referenced.startswith("training_"), f"{source} aponta para {referenced} (dado do usuário)"


async def test_training_tables_keep_no_exact_time(db_session: AsyncSession) -> None:
    result = await db_session.execute(text(
        "SELECT table_name || '.' || column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name LIKE 'training\\_%' "
        "AND data_type IN ('timestamp with time zone', 'timestamp without time zone', 'time without time zone')"
    ))

    assert result.scalars().all() == []
