from abc import ABC, abstractmethod
from datetime import date


class IUsageCounter(ABC):
    """A counter per local day, shared by every API process (Redis in production)."""

    @abstractmethod
    async def increment(self, day: date) -> int:
        """Adds one to the day's count and returns the new value."""
        ...
