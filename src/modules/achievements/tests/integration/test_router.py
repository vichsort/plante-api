"""A rota do módulo num app mínimo: só ela, o envelope e a autenticação do shared."""
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.achievements.api import router
from src.modules.achievements.container import AchievementsContainer
from src.modules.achievements.domain.ports.achievement_repository import (
    AchievementView,
)
from src.modules.achievements.domain.value_objects.ids import AchievementId
from src.shared.api import install_authentication, register_exception_handlers
from src.shared.domain import IAccessTokenVerifier, UnauthorizedError, UserId

USER = UserId(uuid4())
AUTH = {"Authorization": "Bearer valid"}


class _Verifier(IAccessTokenVerifier):
    def verify_access(self, token: str) -> UserId:
        if token != "valid":
            raise UnauthorizedError("Invalid access token.")
        return USER


class _App:
    def __init__(self) -> None:
        self.container = AchievementsContainer()
        self.container.wire(modules=["src.modules.achievements.api.router"])
        app = FastAPI()
        register_exception_handlers(app)
        install_authentication(app, _Verifier)
        app.include_router(router)
        self.client = TestClient(app)

    def use_case(self, provider: providers.Provider[object], result: object = None) -> AsyncMock:
        mock = AsyncMock()
        mock.execute.return_value = result
        provider.override(providers.Object(mock))
        return mock


@pytest.fixture
def api() -> Iterator[_App]:
    app = _App()
    yield app
    app.container.unwire()


def test_lists_the_users_achievements(api: _App) -> None:
    # Arrange
    achievement = AchievementView(
        id=AchievementId(uuid4()), badge_code="first_plant", unlocked_at=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    use_case = api.use_case(api.container.list_achievements_use_case, [achievement])

    # Act
    response = api.client.get("/profile/achievements", headers=AUTH)

    # Assert
    assert response.status_code == 200
    assert response.json()["data"] == [
        {"id": str(achievement.id), "badge_code": "first_plant", "unlocked_at": "2026-10-15T12:00:00Z"},
    ]
    assert use_case.execute.call_args.args[0].user_id == USER


def test_achievements_require_authentication(api: _App) -> None:
    # Act
    response = api.client.get("/profile/achievements")

    # Assert
    assert response.status_code == 401
