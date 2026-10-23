from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.quota.domain.exceptions import ServiceDailyLimitError
from src.modules.quota.domain.ports.usage_counter import IUsageCounter
from src.shared.domain import LocalCalendar


class IProviderBudget(ABC):
    """
    The whole service's daily limit of calls to the paid providers (identifications and diagnoses,
    1 Kindwise credit each), however many accounts there are. The per-user quota does not cover
    that: throwaway accounts each bring their own.
    """

    @abstractmethod
    async def take(self, now: datetime) -> None:
        """
        Takes one call of the day, **right before** calling the provider (after the user's own
        checks). Raises `ServiceDailyLimitError` when the day's calls are gone.
        """
        ...


class ProviderBudget(IProviderBudget):
    def __init__(self, counter: IUsageCounter, calendar: LocalCalendar, daily_limit: int) -> None:
        self.counter = counter
        self.calendar = calendar
        self.daily_limit = daily_limit

    async def take(self, now: datetime) -> None:
        # Counted before the call: a provider failure still spends one (conservative, and the
        # refused attempts past the limit do not matter, the day is over anyway)
        if await self.counter.increment(self.calendar.date_of(now)) > self.daily_limit:
            raise ServiceDailyLimitError(self.daily_limit)
