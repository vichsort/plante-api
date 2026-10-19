from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from src.modules.subscription.domain.entities.subscription import Subscription
from src.modules.subscription.domain.exceptions import (
    PlantLimitExceededError,
    SubscriptionRequiredError,
)
from src.modules.subscription.domain.policies.subscription_policy import (
    SubscriptionPolicy,
)
from src.modules.subscription.domain.value_objects.tier import (
    FeatureCost,
    SubscriptionTier,
)
from src.shared.domain import UserId

NOW = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)
TODAY = date(2026, 10, 16)


def _free(tokens_used_today: int = 0, tokens_day: date | None = TODAY) -> Subscription:
    return Subscription(UserId(uuid4()), SubscriptionTier.FREE, tokens_used_today=tokens_used_today, tokens_day=tokens_day)


def _pro(expires_at: datetime = datetime(2099, 1, 1, tzinfo=UTC), tokens_used_today: int = 0) -> Subscription:
    return Subscription(UserId(uuid4()), SubscriptionTier.PRO, expires_at, tokens_used_today=tokens_used_today, tokens_day=TODAY)


def test_without_a_stored_row_the_user_is_free_with_a_full_quota() -> None:
    # Act
    subscription = Subscription.free_for(UserId(uuid4()))

    # Assert
    assert (subscription.active_tier(NOW), subscription.tokens_used_on(TODAY)) == (SubscriptionTier.FREE, 0)


def test_pro_requires_an_expiration_date() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="expiration"):
        Subscription(UserId(uuid4()), SubscriptionTier.PRO)


def test_free_user_can_add_up_to_limit() -> None:
    # Act & Assert: 2 plantas no jardim, a 3ª ainda cabe
    SubscriptionPolicy.enforce_can_add_to_garden(_free(), plants_in_garden=2, now=NOW)


def test_free_user_exceeds_garden_limit_raises() -> None:
    # Act & Assert
    with pytest.raises(PlantLimitExceededError):
        SubscriptionPolicy.enforce_can_add_to_garden(_free(), plants_in_garden=3, now=NOW)


def test_garden_limit_details_tell_the_count_and_the_limit_apart() -> None:
    # Act: before, both fields carried the limit, as text
    with pytest.raises(PlantLimitExceededError) as raised:
        SubscriptionPolicy.enforce_can_add_to_garden(_free(), plants_in_garden=4, now=NOW)

    # Assert
    assert raised.value.details == {"current_count": 4, "max_allowed": 3}


def test_pro_user_garden_limit() -> None:
    # Arrange
    subscription = _pro()

    # Act & Assert
    SubscriptionPolicy.enforce_can_add_to_garden(subscription, plants_in_garden=49, now=NOW)
    with pytest.raises(PlantLimitExceededError):
        SubscriptionPolicy.enforce_can_add_to_garden(subscription, plants_in_garden=50, now=NOW)


def test_expired_pro_has_free_limits() -> None:
    # Arrange: antes valia o plano gravado, e o PRO vencido seguia com os limites de PRO
    subscription = _pro(expires_at=NOW - timedelta(days=1), tokens_used_today=3)

    # Act & Assert
    with pytest.raises(PlantLimitExceededError):
        SubscriptionPolicy.enforce_can_add_to_garden(subscription, plants_in_garden=3, now=NOW)
    with pytest.raises(SubscriptionRequiredError):
        SubscriptionPolicy.enforce_can_identify_plant(subscription, NOW, TODAY)


def test_token_limit_enforcement() -> None:
    # Arrange
    subscription = _free(tokens_used_today=3)

    # Act & Assert
    with pytest.raises(SubscriptionRequiredError):
        SubscriptionPolicy.enforce_can_identify_plant(subscription, NOW, TODAY)
    with pytest.raises(SubscriptionRequiredError):
        SubscriptionPolicy.enforce_can_diagnose(subscription, NOW, TODAY)


def test_quota_is_full_again_on_the_next_day() -> None:
    # Arrange: antes nada zerava o contador, e o FREE ficava sem tokens para sempre
    subscription = _free(tokens_used_today=3, tokens_day=TODAY - timedelta(days=1))

    # Act & Assert
    SubscriptionPolicy.enforce_can_identify_plant(subscription, NOW, TODAY)
    assert subscription.tokens_used_on(TODAY) == 0


def test_first_charge_of_a_new_day_restarts_the_counter() -> None:
    # Arrange
    subscription = _free(tokens_used_today=3, tokens_day=TODAY - timedelta(days=1))

    # Act
    subscription.consume_tokens(FeatureCost.IDENTIFY, TODAY)

    # Assert
    assert (subscription.tokens_used_today, subscription.tokens_day) == (1, TODAY)


def test_charges_on_the_same_day_add_up() -> None:
    # Arrange
    subscription = _free(tokens_used_today=1)

    # Act
    subscription.consume_tokens(FeatureCost.DEEP_ANALYSIS, TODAY)

    # Assert
    assert subscription.tokens_used_on(TODAY) == 3


@pytest.mark.parametrize("used, can_enrich", [(0, True), (1, True), (2, False)])
def test_diagnosis_enrichment_only_when_both_tokens_fit(used: int, can_enrich: bool) -> None:
    # Arrange: FREE tem 3; diagnóstico custa 1 e o complemento do Gemini mais 1
    subscription = _free(tokens_used_today=used)

    # Act & Assert
    assert SubscriptionPolicy.can_enrich_diagnosis(subscription, NOW, TODAY) is can_enrich


def test_identifying_does_not_depend_on_garden_size() -> None:
    # Act & Assert: identificar não adiciona planta ao jardim, então jardim cheio não bloqueia
    SubscriptionPolicy.enforce_can_identify_plant(_free(), NOW, TODAY)


def test_upgrade_starts_with_a_full_pro_quota() -> None:
    # Arrange
    subscription = _free(tokens_used_today=3)

    # Act
    subscription.upgrade_to_pro(expires_at=NOW + timedelta(days=30), current_time=NOW)

    # Assert
    assert subscription.active_tier(NOW) == SubscriptionTier.PRO
    assert subscription.active_tier(NOW).remaining_tokens(subscription.tokens_used_on(TODAY)) == 30
