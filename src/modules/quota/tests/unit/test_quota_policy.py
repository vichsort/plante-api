from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.exceptions import (
    DailyQuotaExceededError,
    PlantLimitExceededError,
)
from src.modules.quota.domain.policies.quota_policy import QuotaPolicy
from src.modules.quota.domain.value_objects.level import FeatureCost, QuotaLevel
from src.shared.domain import UserId

NOW = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)
TODAY = date(2026, 10, 16)


def _standard(tokens_used_today: int = 0, tokens_day: date | None = TODAY) -> Quota:
    return Quota(UserId(uuid4()), QuotaLevel.STANDARD, tokens_used_today=tokens_used_today, tokens_day=tokens_day)


def _extended(expires_at: datetime = datetime(2099, 1, 1, tzinfo=UTC), tokens_used_today: int = 0) -> Quota:
    return Quota(UserId(uuid4()), QuotaLevel.EXTENDED, expires_at, tokens_used_today=tokens_used_today, tokens_day=TODAY)


def test_without_a_stored_row_the_user_is_standard_with_a_full_quota() -> None:
    # Act
    quota = Quota.standard_for(UserId(uuid4()))

    # Assert
    assert (quota.active_level(NOW), quota.tokens_used_on(TODAY)) == (QuotaLevel.STANDARD, 0)


def test_extended_requires_an_expiration_date() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="expiration"):
        Quota(UserId(uuid4()), QuotaLevel.EXTENDED)


def test_standard_has_no_expiration_date() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="expiration"):
        Quota(UserId(uuid4()), QuotaLevel.STANDARD, expires_at=NOW)


def test_standard_user_can_add_up_to_limit() -> None:
    # Act & Assert: 2 plantas no jardim, a 3ª ainda cabe
    QuotaPolicy.enforce_can_add_to_garden(_standard(), plants_in_garden=2, now=NOW)


def test_standard_user_exceeds_garden_limit_raises() -> None:
    # Act & Assert
    with pytest.raises(PlantLimitExceededError):
        QuotaPolicy.enforce_can_add_to_garden(_standard(), plants_in_garden=3, now=NOW)


def test_garden_limit_details_tell_the_count_and_the_limit_apart() -> None:
    # Act: before, both fields carried the limit, as text
    with pytest.raises(PlantLimitExceededError) as raised:
        QuotaPolicy.enforce_can_add_to_garden(_standard(), plants_in_garden=4, now=NOW)

    # Assert
    assert raised.value.details == {"quota": "standard", "current_count": 4, "max_allowed": 3}
    assert raised.value.message == "The standard quota allows up to 3 plants in the garden."


def test_daily_quota_tells_the_level_and_does_not_assume_standard() -> None:
    # Arrange: before, a Pro user out of tokens was told to subscribe to Pro
    quota = _extended(tokens_used_today=10)

    # Act
    with pytest.raises(DailyQuotaExceededError) as raised:
        QuotaPolicy.enforce_can_identify_plant(quota, NOW, TODAY)

    # Assert
    assert raised.value.details == {"quota": "extended", "used_today": 10, "daily_limit": 10}
    assert "plan" not in raised.value.message.lower()
    assert "subscribe" not in raised.value.message.lower()


def test_extended_user_garden_limit() -> None:
    # Arrange
    quota = _extended()

    # Act & Assert
    QuotaPolicy.enforce_can_add_to_garden(quota, plants_in_garden=9, now=NOW)
    with pytest.raises(PlantLimitExceededError):
        QuotaPolicy.enforce_can_add_to_garden(quota, plants_in_garden=10, now=NOW)


def test_expired_extended_has_standard_limits() -> None:
    # Arrange: before, the stored plan counted, and an expired PRO kept the PRO limits
    quota = _extended(expires_at=NOW - timedelta(days=1), tokens_used_today=3)

    # Act & Assert
    with pytest.raises(PlantLimitExceededError):
        QuotaPolicy.enforce_can_add_to_garden(quota, plants_in_garden=3, now=NOW)
    with pytest.raises(DailyQuotaExceededError):
        QuotaPolicy.enforce_can_identify_plant(quota, NOW, TODAY)


def test_token_limit_enforcement() -> None:
    # Arrange
    quota = _standard(tokens_used_today=3)

    # Act & Assert
    with pytest.raises(DailyQuotaExceededError):
        QuotaPolicy.enforce_can_identify_plant(quota, NOW, TODAY)
    with pytest.raises(DailyQuotaExceededError):
        QuotaPolicy.enforce_can_diagnose(quota, NOW, TODAY)


def test_quota_is_full_again_on_the_next_day() -> None:
    # Arrange: before, nothing reset the counter, and a FREE user ran out of tokens for good
    quota = _standard(tokens_used_today=3, tokens_day=TODAY - timedelta(days=1))

    # Act & Assert
    QuotaPolicy.enforce_can_identify_plant(quota, NOW, TODAY)
    assert quota.tokens_used_on(TODAY) == 0


def test_first_charge_of_a_new_day_restarts_the_counter() -> None:
    # Arrange
    quota = _standard(tokens_used_today=3, tokens_day=TODAY - timedelta(days=1))

    # Act
    quota.consume_tokens(FeatureCost.IDENTIFY, TODAY)

    # Assert
    assert (quota.tokens_used_today, quota.tokens_day) == (1, TODAY)


def test_charges_on_the_same_day_add_up() -> None:
    # Arrange
    quota = _standard(tokens_used_today=1)

    # Act
    quota.consume_tokens(FeatureCost.DEEP_ANALYSIS, TODAY)

    # Assert
    assert quota.tokens_used_on(TODAY) == 3


@pytest.mark.parametrize("used, can_enrich", [(0, True), (1, True), (2, False)])
def test_diagnosis_enrichment_only_when_both_tokens_fit(used: int, can_enrich: bool) -> None:
    # Arrange: standard tem 3; diagnóstico custa 1 e o complemento do Gemini mais 1
    quota = _standard(tokens_used_today=used)

    # Act & Assert
    assert QuotaPolicy.can_enrich_diagnosis(quota, NOW, TODAY) is can_enrich


def test_identifying_does_not_depend_on_garden_size() -> None:
    # Act & Assert: identificar não adiciona planta ao jardim, então jardim cheio não bloqueia
    QuotaPolicy.enforce_can_identify_plant(_standard(), NOW, TODAY)
