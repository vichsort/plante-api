from datetime import UTC, datetime

import pytest

from src.domain.entities.user import User
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.domain.value_objects.user_location import UserLocation


def test_user_creation_and_email_validation():
    now = datetime.now(UTC)
    user = User.create_new(
        email="dev@plante.org",
        hashed_password="hashed_pass",
        location=UserLocation(country="BR", state="SP"),
        current_time=now,
    )

    assert user.email == "dev@plante.org"
    assert user.is_verified is False
    assert user.subscription == SubscriptionTier.FREE

    with pytest.raises(ValueError, match="Invalid email address"):
        User.create_new(
            email="invalid-email",
            hashed_password="hash",
            location=UserLocation(country="BR", state="SP"),
            current_time=now,
        )

def test_user_email_is_normalized_on_creation_and_change():
    user = User.create_new(
        email=" Dev@Plante.ORG ",
        hashed_password="hash",
        location=UserLocation(country="BR", state="SP"),
        current_time=datetime.now(UTC),
    )
    assert user.email == "dev@plante.org"

    user.request_email_change("  Novo@Plante.org")
    assert (user.email, user.pending_email) == ("dev@plante.org", "novo@plante.org")
    user.confirm_email_change()
    assert (user.email, user.pending_email) == ("novo@plante.org", None)
