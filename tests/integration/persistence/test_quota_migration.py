"""The quota migration renames the plans and takes away every PRO granted by the old public route."""
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from sqlalchemy import Connection, create_engine, text

_ROOT = Path(__file__).parents[3]
_BEFORE = "b8e2d4f6a1c3"


def _migrate(connection: Connection, direction: str, revision: str) -> None:
    config = AlembicConfig(str(_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_ROOT / "migrations"))
    config.attributes["connection"] = connection
    getattr(alembic_command, direction)(config, revision)


def _account(connection: Connection) -> str:
    user_id = str(uuid4())
    connection.execute(
        text(
            "INSERT INTO users (id, email, hashed_password, location_country, location_state, is_verified, created_at, updated_at)"
            " VALUES (:id, :email, 'hash', 'BR', 'SP', true, now(), now())"
        ),
        {"id": user_id, "email": f"{user_id}@plante.org"},
    )
    return user_id


def test_every_pro_row_becomes_standard_without_a_deadline(postgres_url: str) -> None:
    # Arrange: the schema before the migration, with a self-granted PRO and a FREE that spent tokens
    engine = create_engine(postgres_url)
    try:
        with engine.connect() as connection, connection.begin() as transaction:  # DDL included, undone at the end
            _migrate(connection, "downgrade", _BEFORE)
            pro, free = _account(connection), _account(connection)
            connection.execute(
                text(
                    "INSERT INTO subscriptions (user_id, tier, expires_at, tokens_used_today, created_at, updated_at)"
                    " VALUES (:pro, 'PRO', :expires_at, 7, now(), now()), (:free, 'FREE', NULL, 2, now(), now())"
                ),
                {"pro": pro, "free": free, "expires_at": datetime.now(UTC) + timedelta(days=9999)},
            )

            # Act
            _migrate(connection, "upgrade", "head")

            # Assert
            rows = connection.execute(
                text("SELECT user_id::text, level::text, expires_at, tokens_used_today FROM quotas"),
            ).all()
            assert sorted(map(tuple, rows)) == sorted([(pro, "standard", None, 7), (free, "standard", None, 2)])
            transaction.rollback()
    finally:
        engine.dispose()
