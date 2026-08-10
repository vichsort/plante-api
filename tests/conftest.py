import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.adapters.persistence.models.base import Base

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

@pytest_asyncio.fixture
async def db_session():
    """Fixture de banco de dados assíncrono em memória (SQLite + aiosqlite)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()
