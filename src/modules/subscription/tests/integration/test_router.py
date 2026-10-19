"""A rota do módulo num app mínimo: só ela, o envelope e a autenticação do shared."""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.subscription.api import router
from src.modules.subscription.container import SubscriptionContainer
from src.modules.subscription.domain.entities.subscription import Subscription
from src.modules.subscription.domain.value_objects.tier import SubscriptionTier
from src.shared.api import install_authentication, register_exception_handlers
from src.shared.domain import IAccessTokenVerifier, UnauthorizedError, UserId

USER = UserId(uuid4())


class _Verifier(IAccessTokenVerifier):
    def verify_access(self, token: str) -> UserId:
        if token != "valid":
            raise UnauthorizedError("Invalid access token.")
        return USER


def _client(use_case: AsyncMock) -> TestClient:
    container = SubscriptionContainer()
    container.upgrade_subscription_use_case.override(providers.Object(use_case))
    container.wire(modules=["src.modules.subscription.api.router"])
    app = FastAPI()
    register_exception_handlers(app)
    install_authentication(app, _Verifier)
    app.include_router(router)
    return TestClient(app)


def test_upgrade_returns_the_new_plan() -> None:
    # Arrange
    expires_at = datetime.now(UTC) + timedelta(days=365)
    use_case = AsyncMock()
    use_case.execute.return_value = Subscription(USER, SubscriptionTier.PRO, expires_at)

    # Act
    response = _client(use_case).post(
        "/profile/subscription/upgrade", json={"plan_duration_days": 365}, headers={"Authorization": "Bearer valid"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["data"]["subscription"] == "PRO"
    assert response.json()["data"]["user_id"] == str(USER)
    assert use_case.execute.call_args.args[0].user_id == USER


def test_upgrade_requires_authentication() -> None:
    # Act
    response = _client(AsyncMock()).post("/profile/subscription/upgrade", json={"plan_duration_days": 365})

    # Assert
    assert response.status_code == 401
