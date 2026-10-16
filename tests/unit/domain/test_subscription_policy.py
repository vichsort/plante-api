from datetime import UTC, date, datetime, timedelta

import pytest

from src.domain.entities.user import User
from src.domain.exceptions import PlantLimitExceededError, SubscriptionRequiredError
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.value_objects.subscription_tier import FeatureCost, SubscriptionTier
from src.domain.value_objects.user_location import UserLocation

NOW = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)
TODAY = date(2026, 10, 16)


def make_user(
    subscription: SubscriptionTier = SubscriptionTier.FREE,
    tokens_used_today: int = 0,
    tokens_day: date | None = TODAY,
    subscription_expires_at: datetime | None = None,
) -> User:
    return User(
        id=None,
        email="test@example.com",
        hashed_password="hash",
        location=UserLocation(country="BR", state="SP"),
        is_verified=True,
        subscription=subscription,
        created_at=NOW,
        tokens_used_today=tokens_used_today,
        tokens_day=tokens_day,
        subscription_expires_at=subscription_expires_at,
    )


def _pro(expires_at: datetime = datetime(2099, 1, 1, tzinfo=UTC), tokens_used_today: int = 0) -> User:
    return make_user(SubscriptionTier.PRO, tokens_used_today=tokens_used_today, subscription_expires_at=expires_at)


def test_free_user_can_add_up_to_limit() -> None:
    # Act & Assert: 2 plantas no jardim, a 3ª ainda cabe
    SubscriptionPolicy.enforce_can_add_to_garden(make_user(), plants_in_garden=2, now=NOW)


def test_free_user_exceeds_garden_limit_raises() -> None:
    # Act & Assert
    with pytest.raises(PlantLimitExceededError):
        SubscriptionPolicy.enforce_can_add_to_garden(make_user(), plants_in_garden=3, now=NOW)


def test_pro_user_garden_limit() -> None:
    # Arrange
    user = _pro()

    # Act & Assert
    SubscriptionPolicy.enforce_can_add_to_garden(user, plants_in_garden=49, now=NOW)
    with pytest.raises(PlantLimitExceededError):
        SubscriptionPolicy.enforce_can_add_to_garden(user, plants_in_garden=50, now=NOW)


def test_expired_pro_has_free_limits() -> None:
    # Arrange: antes valia o plano gravado, e o PRO vencido seguia com os limites de PRO
    user = _pro(expires_at=NOW - timedelta(days=1), tokens_used_today=3)

    # Act & Assert
    with pytest.raises(PlantLimitExceededError):
        SubscriptionPolicy.enforce_can_add_to_garden(user, plants_in_garden=3, now=NOW)
    with pytest.raises(SubscriptionRequiredError):
        SubscriptionPolicy.enforce_can_identify_plant(user, NOW, TODAY)


def test_token_limit_enforcement() -> None:
    # Arrange
    user = make_user(tokens_used_today=3)

    # Act & Assert
    with pytest.raises(SubscriptionRequiredError):
        SubscriptionPolicy.enforce_can_identify_plant(user, NOW, TODAY)
    with pytest.raises(SubscriptionRequiredError):
        SubscriptionPolicy.enforce_can_diagnose(user, NOW, TODAY)


def test_quota_is_full_again_on_the_next_day() -> None:
    # Arrange: antes nada zerava o contador, e o FREE ficava sem tokens para sempre
    user = make_user(tokens_used_today=3, tokens_day=TODAY - timedelta(days=1))

    # Act & Assert
    SubscriptionPolicy.enforce_can_identify_plant(user, NOW, TODAY)
    assert user.tokens_used_on(TODAY) == 0


def test_first_charge_of_a_new_day_restarts_the_counter() -> None:
    # Arrange
    user = make_user(tokens_used_today=3, tokens_day=TODAY - timedelta(days=1))

    # Act
    user.consume_tokens(FeatureCost.IDENTIFY, TODAY)

    # Assert
    assert (user.tokens_used_today, user.tokens_day) == (1, TODAY)


def test_charges_on_the_same_day_add_up() -> None:
    # Arrange
    user = make_user(tokens_used_today=1)

    # Act
    user.consume_tokens(FeatureCost.DEEP_ANALYSIS, TODAY)

    # Assert
    assert user.tokens_used_on(TODAY) == 3


@pytest.mark.parametrize("used, can_enrich", [(0, True), (1, True), (2, False)])
def test_diagnosis_enrichment_only_when_both_tokens_fit(used: int, can_enrich: bool) -> None:
    # Arrange: FREE tem 3; diagnóstico custa 1 e o complemento do Gemini mais 1
    user = make_user(tokens_used_today=used)

    # Act & Assert
    assert SubscriptionPolicy.can_enrich_diagnosis(user, NOW, TODAY) is can_enrich


def test_identifying_does_not_depend_on_garden_size() -> None:
    # Act & Assert: identificar não adiciona planta ao jardim, então jardim cheio não bloqueia
    SubscriptionPolicy.enforce_can_identify_plant(make_user(), NOW, TODAY)
