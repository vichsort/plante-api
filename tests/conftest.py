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
from redis.asyncio import Redis
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

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

from src.adapters.cache.redis_client import RedisClient
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

def _start_or_skip[C: DockerContainer](container: C) -> C:
    """Sobe o contêiner; sem Docker, pula o teste localmente e falha no CI."""
    try:
        return container.start()
    except DockerException as exc:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"Docker indisponível para os testes de infraestrutura: {exc}")


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """Postgres real em contêiner, com o schema criado pelas migrations do Alembic."""
    container = _start_or_skip(PostgresContainer("postgres:16-alpine", driver="psycopg"))

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
async def db_connection(postgres_url: str) -> AsyncIterator[AsyncConnection]:
    """
    Conexão com uma transação externa desfeita ao final: os testes não enxergam dados uns dos
    outros. Sessões abertas nela usam savepoints, então `commit()` só fecha um savepoint.
    """
    engine = create_async_engine(postgres_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
def session_factory(db_connection: AsyncConnection) -> async_sessionmaker[AsyncSession]:
    """Fábrica de sessões na conexão do teste (a mesma que o `SqlAlchemyUnitOfWork` recebe)."""
    return async_sessionmaker(
        bind=db_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


@pytest_asyncio.fixture
async def db_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    """Redis real em contêiner (o extra `redis` do testcontainers exige redis-py 7; usamos o 5)."""
    container = _start_or_skip(
        DockerContainer("redis:7-alpine")
        .with_exposed_ports(6379)
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
    )
    try:
        yield f"redis://{container.get_container_host_ip()}:{container.get_exposed_port(6379)}/0"
    finally:
        container.stop()


@pytest_asyncio.fixture
async def raw_redis(redis_url: str) -> AsyncIterator[Redis]:
    """Cliente redis-py cru, para conferir o que foi gravado (TTL, valor). Banco limpo por teste."""
    redis = Redis.from_url(redis_url)
    await redis.flushdb()
    try:
        yield redis
    finally:
        await redis.aclose()


@pytest.fixture
def redis_client(raw_redis: Redis) -> RedisClient:
    return RedisClient(raw_redis)
