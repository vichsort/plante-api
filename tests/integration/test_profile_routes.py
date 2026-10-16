import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.domain.ports.achievement_repository import AchievementView
from src.domain.value_objects.ids import AchievementId
from tests.factories import NOW


def test_list_achievements_route_success(client: TestClient, auth_headers: dict[str, str]):
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = [
        AchievementView(id=AchievementId(uuid.uuid4()), badge_code="FIRST_PLANT_ADDED", unlocked_at=NOW),
    ]

    with client.app.state.container.use_cases.list_user_achievements_use_case.override(mock_use_case):
        response = client.get("/profile/achievements", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["data"]) == 1
    assert payload["data"][0]["badge_code"] == "FIRST_PLANT_ADDED"
