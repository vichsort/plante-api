import os
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
import pytest_asyncio
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from docker.errors import DockerException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer

# Define variáveis de ambiente dummy ANTES de importar src.main
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_USER"] = "test_user"
os.environ["DB_PASSWORD"] = "test_pass"
os.environ["DB_NAME"] = "test_db"
os.environ["REDIS_PASSWORD"] = "test_redis"
os.environ["REDIS_ENDPOINT"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["SECRET_KEY"] = "supersecretkeyfortesting1234567890"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["AWS_ACCESS_KEY_ID"] = "test_aws_key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test_aws_secret"
os.environ["SES_SENDER_EMAIL"] = "noreply@test.org"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "test_credentials.json"

from src.main import app

_ROOT = Path(__file__).parents[1]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

@pytest.fixture
def test_user_id() -> str:
    return str(uuid.uuid4())

@pytest.fixture
def auth_headers(test_user_id: str) -> dict[str, str]:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": test_user_id,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        "supersecretkeyfortesting1234567890",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """Postgres real em contêiner, com o schema criado pelas migrations do Alembic."""
    try:
        container = PostgresContainer("postgres:16-alpine", driver="psycopg").start()
    except DockerException as exc:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"Docker indisponível para os testes de banco: {exc}")

    try:
        url = container.get_connection_url()
        engine = create_engine(url)
        with engine.begin() as connection:
            config = AlembicConfig(str(_ROOT / "alembic.ini"))
            config.set_main_option("script_location", str(_ROOT / "migrations"))
            config.attributes["connection"] = connection
            alembic_command.upgrade(config, "head")
        engine.dispose()
        yield url
    finally:
        container.stop()


@pytest_asyncio.fixture
async def db_session(postgres_url: str) -> AsyncIterator[AsyncSession]:
    """
    Sessão no Postgres de teste. Tudo roda numa transação desfeita ao final; `commit()` nos
    testes só fecha um savepoint, então os testes não enxergam dados uns dos outros.
    """
    engine = create_async_engine(postgres_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()
