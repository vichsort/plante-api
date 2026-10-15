from datetime import UTC, datetime

import pytest

from src.domain.entities.user import User
from src.domain.exceptions import PlantLimitExceededError, SubscriptionRequiredError
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.domain.value_objects.user_location import UserLocation


def make_user(
    subscription: SubscriptionTier = SubscriptionTier.FREE,
    tokens_used_today: int = 0,
    subscription_expires_at: datetime | None = None,
) -> User:
    return User(
        id=None,
        email="test@example.com",
        hashed_password="hash",
        location=UserLocation(country="BR", state="SP"),
        is_verified=True,
        subscription=subscription,
        created_at=datetime.now(UTC),
        tokens_used_today=tokens_used_today,
        subscription_expires_at=subscription_expires_at,
    )

def test_free_user_can_add_up_to_limit():
    # 2 plantas no jardim — pode adicionar a 3ª (limite FREE é 3)
    SubscriptionPolicy.enforce_can_add_to_garden(make_user(SubscriptionTier.FREE), plants_in_garden=2)

def test_free_user_exceeds_garden_limit_raises():
    # Já tem 3 plantas no jardim — lançar PlantLimitExceededError
    with pytest.raises(PlantLimitExceededError):
        SubscriptionPolicy.enforce_can_add_to_garden(make_user(SubscriptionTier.FREE), plants_in_garden=3)

def test_pro_user_garden_limit():
    user = make_user(
        SubscriptionTier.PRO,
        subscription_expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    # Usuário PRO com 49 plantas pode adicionar
    SubscriptionPolicy.enforce_can_add_to_garden(user, plants_in_garden=49)

    user_full = make_user(
        SubscriptionTier.PRO,
        subscription_expires_at=datetime(2099, 1, 1, tzinfo=UTC),
    )
    # Limite PRO de 50 atingido
    with pytest.raises(PlantLimitExceededError):
        SubscriptionPolicy.enforce_can_add_to_garden(user_full, plants_in_garden=50)

def test_token_limit_enforcement():
    user = make_user(SubscriptionTier.FREE, tokens_used_today=3)
    with pytest.raises(SubscriptionRequiredError):
        SubscriptionPolicy.enforce_can_identify_plant(user)


def test_identifying_does_not_depend_on_garden_size():
    # Identificar não adiciona planta ao jardim: jardim cheio não bloqueia (antes bloqueava)
    SubscriptionPolicy.enforce_can_identify_plant(make_user(SubscriptionTier.FREE))
