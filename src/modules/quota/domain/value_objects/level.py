from dataclasses import dataclass
from enum import IntEnum, StrEnum


class FeatureCost(IntEnum):
    """Token cost of each AI action."""
    IDENTIFY = 1
    DEEP_ANALYSIS = 2
    DIAGNOSIS = 1             # Kindwise diagnosis
    DIAGNOSIS_ENRICHMENT = 1  # Gemini add-on, charged only when delivered


class QuotaLevel(StrEnum):
    """`standard` is everyone's; `extended` is granted by the maintainer, for free and with a deadline."""
    STANDARD = "standard"
    EXTENDED = "extended"


@dataclass(frozen=True, slots=True)
class QuotaLimits:
    """What one level allows: plants in the garden and AI tokens a day."""
    max_plants: int
    daily_tokens: int

    def __post_init__(self) -> None:
        if self.max_plants < 0 or self.daily_tokens < 0:
            raise ValueError("Quota limits cannot be negative.")

    def can_add_plant(self, current_plant_count: int) -> bool:
        return current_plant_count < self.max_plants

    def can_consume(self, feature_cost: FeatureCost, tokens_used_today: int) -> bool:
        if tokens_used_today < 0:
            raise ValueError("tokens_used_today cannot be negative.")
        return (tokens_used_today + feature_cost.value) <= self.daily_tokens

    def remaining_tokens(self, tokens_used_today: int) -> int:
        return self.daily_tokens - tokens_used_today


@dataclass(frozen=True, slots=True)
class LevelLimits:
    """The limits of each level."""
    standard: QuotaLimits
    extended: QuotaLimits

    def of(self, level: QuotaLevel) -> QuotaLimits:
        return self.extended if level is QuotaLevel.EXTENDED else self.standard


DEFAULT_LIMITS = LevelLimits(
    standard=QuotaLimits(max_plants=3, daily_tokens=3),
    extended=QuotaLimits(max_plants=10, daily_tokens=10),
)
