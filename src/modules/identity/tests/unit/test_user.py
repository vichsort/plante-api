from datetime import UTC, datetime

import pytest

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.value_objects.user_location import UserLocation

NOW = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)


def _new(email: str) -> User:
    return User.create_new(
        email=email, hashed_password="hash", location=UserLocation(country="BR", state="SP"), current_time=NOW,
    )


def test_new_user_starts_unverified() -> None:
    # Act
    user = _new("dev@plante.org")

    # Assert
    assert (user.email, user.is_verified) == ("dev@plante.org", False)


def test_invalid_email_is_rejected() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid email address"):
        _new("invalid-email")


def test_email_is_normalized_on_creation() -> None:
    # Act
    user = _new(" Dev@Plante.ORG ")

    # Assert
    assert user.email == "dev@plante.org"


def test_email_change_waits_for_the_code() -> None:
    # Arrange
    user = _new("dev@plante.org")

    # Act
    user.request_email_change("  Novo@Plante.org")

    # Assert: o e-mail atual segue valendo até a confirmação
    assert (user.email, user.pending_email) == ("dev@plante.org", "novo@plante.org")


def test_confirming_the_change_swaps_the_email() -> None:
    # Arrange
    user = _new("dev@plante.org")
    user.request_email_change("novo@plante.org")

    # Act
    user.confirm_email_change()

    # Assert
    assert (user.email, user.pending_email) == ("novo@plante.org", None)


def test_location_is_normalized() -> None:
    # Act
    location = UserLocation(country=" br ", state="santa catarina")

    # Assert
    assert (location.country, location.state) == ("BR", "Santa Catarina")
