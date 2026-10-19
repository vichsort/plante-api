from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.modules.quota.domain.value_objects.level import FeatureCost, QuotaLevel
from src.shared.domain import UserId


@dataclass(slots=True)
class Quota:
    """
    A user's quota level and daily token counter. A user without a stored row is `standard` with a
    full quota (`standard_for`), so signing up does not need to create anything here.
    """

    user_id: UserId
    level: QuotaLevel
    expires_at: datetime | None = None
    tokens_used_today: int = 0
    # Local day `tokens_used_today` refers to: on any other day the counter is zero
    tokens_day: date | None = None

    def __post_init__(self) -> None:
        if self.tokens_used_today < 0:
            raise ValueError("tokens_used_today cannot be negative.")
        if self.level is QuotaLevel.EXTENDED and self.expires_at is None:
            raise ValueError("An extended quota requires an expiration date.")
        if self.level is QuotaLevel.STANDARD and self.expires_at is not None:
            raise ValueError("A standard quota has no expiration date.")

    @classmethod
    def standard_for(cls, user_id: UserId) -> Quota:
        return cls(user_id=user_id, level=QuotaLevel.STANDARD)

    def tokens_used_on(self, today: date) -> int:
        """The quota is daily: the stored counter only counts on the day it refers to."""
        return self.tokens_used_today if self.tokens_day == today else 0

    def consume_tokens(self, cost: FeatureCost, today: date) -> None:
        """Resets on the first charge of a new day, without a cron (the policy decides whether it may)."""
        self.tokens_used_today = self.tokens_used_on(today) + cost.value
        self.tokens_day = today

    def grant_extended(self, expires_at: datetime, current_time: datetime) -> None:
        """The deadline counts from now (it replaces any earlier one), and the extended quota starts full."""
        if expires_at <= current_time:
            raise ValueError("expires_at must be a future datetime.")
        self.level = QuotaLevel.EXTENDED
        self.expires_at = expires_at
        self.tokens_used_today = 0

    def revoke_extended(self) -> None:
        """Back to standard right away; today's tokens stay spent."""
        self.level = QuotaLevel.STANDARD
        self.expires_at = None

    def is_extended(self, current_time: datetime) -> bool:
        return (
            self.level is QuotaLevel.EXTENDED
            and self.expires_at is not None
            and current_time < self.expires_at
        )

    def active_level(self, current_time: datetime) -> QuotaLevel:
        """An expired extended quota counts as standard."""
        return QuotaLevel.EXTENDED if self.is_extended(current_time) else QuotaLevel.STANDARD
