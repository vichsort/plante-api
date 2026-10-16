"""Fixtures dos testes da API antiga (rotas com use cases falsos). A infraestrutura vem do testbed."""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from src.bootstrap.wiring import wire
from src.main import app


@pytest.fixture
def client() -> TestClient:
    # A ligação das rotas é global: outro teste pode ter ligado outro container
    wire(app.state.container)
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
