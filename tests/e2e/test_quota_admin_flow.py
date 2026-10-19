"""The maintainer's command against the real app: the extended quota is what the API enforces."""
import pytest

from src.bootstrap.quota_admin import run
from src.main import app
from src.shared.domain import UserNotFoundError
from tests.e2e.conftest import Api


async def _identify_times(api: Api, headers: dict[str, str], times: int) -> list[int]:
    return [(await api.identify(headers)).status_code for _ in range(times)]


async def test_granted_user_identifies_past_the_standard_quota(api: Api) -> None:
    # Arrange: the standard quota (3 a day) is used up
    email = "school@plante.org"
    headers = await api.signed_up(email)
    assert await _identify_times(api, headers, 4) == [200, 200, 200, 429]

    # Act
    granted = await run(app.state.container, ["grant", email, "--days", "90"])

    # Assert: the extended quota starts full
    assert granted.startswith(f"Extended quota for {email} until ")
    assert await _identify_times(api, headers, 1) == [200]


async def test_revoked_user_is_back_to_the_standard_quota(api: Api) -> None:
    # Arrange: granted, and 1 token spent on the extended quota
    headers = await api.signed_up("school@plante.org")
    await run(app.state.container, ["grant", "school@plante.org", "--days", "90"])
    assert await _identify_times(api, headers, 1) == [200]

    # Act: the email as the maintainer typed it
    revoked = await run(app.state.container, ["revoke", " School@Plante.org"])

    # Assert: the standard 3 allow 2 more today
    assert revoked == " School@Plante.org is back to the standard quota."
    assert await _identify_times(api, headers, 2) == [200, 200]
    response = await api.identify(headers)
    assert response.status_code == 429
    assert response.json()["error"]["details"]["quota"] == "standard"


async def test_unknown_email_is_reported(api: Api) -> None:
    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await run(app.state.container, ["grant", "nobody@plante.org", "--days", "30"])


@pytest.mark.parametrize("days", ["0", "366", "-1"])
async def test_days_out_of_bounds_are_refused_before_touching_anything(api: Api, days: str) -> None:
    # Act & Assert: argparse exits with a usage error
    with pytest.raises(SystemExit):
        await run(app.state.container, ["grant", "school@plante.org", "--days", days])
