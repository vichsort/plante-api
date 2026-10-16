"""Fixtures dos testes da API antiga (rotas com use cases falsos). A infraestrutura vem do testbed."""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

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
