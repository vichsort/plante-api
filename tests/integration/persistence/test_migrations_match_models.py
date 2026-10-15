"""O schema criado pelas migrations bate com os modelos (o autogenerate não geraria nada)."""
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from src.adapters.persistence.models import Base


def test_migrations_match_models(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    try:
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()

    assert diff == []
