from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.policies.quota_policy import (
    QuotaPolicy,
)
from src.modules.quota.domain.ports.unit_of_work import IQuotaUnitOfWork
from src.modules.quota.domain.value_objects.tier import FeatureCost
from src.shared.domain import LocalCalendar, UserId


class ITokenWallet(ABC):
    """
    A cota diária de tokens, para quem consome IA. Ela protege os créditos dos provedores, então é
    regra de verdade (o plano em si é demonstrativo). O uso esperado:

    1. conferir o saldo (`ensure_can_*`) **antes** das chamadas caras;
    2. chamar os provedores fora da transação;
    3. cobrar (`charge`) **dentro da transação de quem chama**, junto com o que foi entregue.
    """

    @abstractmethod
    async def ensure_can_identify(self, user_id: UserId, now: datetime) -> None:
        """Lança `DailyQuotaExceededError` sem saldo para uma identificação."""
        ...

    @abstractmethod
    async def ensure_can_diagnose(self, user_id: UserId, now: datetime) -> None:
        """Lança `DailyQuotaExceededError` sem saldo para o diagnóstico básico."""
        ...

    @abstractmethod
    async def can_enrich_diagnosis(self, user_id: UserId, now: datetime) -> bool:
        """Cabem o diagnóstico e o complemento do Gemini?"""
        ...

    @abstractmethod
    async def charge(self, user_id: UserId, cost: FeatureCost, now: datetime) -> None:
        """Cobra na transação de quem chama. Lança `UserNotFoundError` se o usuário não tem conta."""
        ...


class TokenWallet(ITokenWallet):
    def __init__(self, uow: IQuotaUnitOfWork, calendar: LocalCalendar) -> None:
        self.uow = uow
        self.calendar = calendar

    async def ensure_can_identify(self, user_id: UserId, now: datetime) -> None:
        QuotaPolicy.enforce_can_identify_plant(await self._current(user_id), now, self.calendar.date_of(now))

    async def ensure_can_diagnose(self, user_id: UserId, now: datetime) -> None:
        QuotaPolicy.enforce_can_diagnose(await self._current(user_id), now, self.calendar.date_of(now))

    async def can_enrich_diagnosis(self, user_id: UserId, now: datetime) -> bool:
        return QuotaPolicy.can_enrich_diagnosis(await self._current(user_id), now, self.calendar.date_of(now))

    async def charge(self, user_id: UserId, cost: FeatureCost, now: datetime) -> None:
        async with self.uow as uow:
            # Service não faz commit: fora de uma transação de quem chama, a cobrança se perderia
            if not uow.joined:
                raise RuntimeError("TokenWallet.charge must be called inside the caller's unit of work.")
            quota = await uow.quotas.lock(user_id)
            quota.consume_tokens(cost, self.calendar.date_of(now))
            await uow.quotas.save(quota)

    async def _current(self, user_id: UserId) -> Quota:
        async with self.uow as uow:
            return await uow.quotas.get(user_id) or Quota.free_for(user_id)
