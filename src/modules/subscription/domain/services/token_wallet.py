from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.subscription.domain.entities.subscription import Subscription
from src.modules.subscription.domain.policies.subscription_policy import (
    SubscriptionPolicy,
)
from src.modules.subscription.domain.ports.unit_of_work import ISubscriptionUnitOfWork
from src.modules.subscription.domain.value_objects.tier import FeatureCost
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
        """Lança `SubscriptionRequiredError` sem saldo para uma identificação."""
        ...

    @abstractmethod
    async def ensure_can_diagnose(self, user_id: UserId, now: datetime) -> None:
        """Lança `SubscriptionRequiredError` sem saldo para o diagnóstico básico."""
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
    def __init__(self, uow: ISubscriptionUnitOfWork, calendar: LocalCalendar) -> None:
        self.uow = uow
        self.calendar = calendar

    async def ensure_can_identify(self, user_id: UserId, now: datetime) -> None:
        SubscriptionPolicy.enforce_can_identify_plant(await self._current(user_id), now, self.calendar.date_of(now))

    async def ensure_can_diagnose(self, user_id: UserId, now: datetime) -> None:
        SubscriptionPolicy.enforce_can_diagnose(await self._current(user_id), now, self.calendar.date_of(now))

    async def can_enrich_diagnosis(self, user_id: UserId, now: datetime) -> bool:
        return SubscriptionPolicy.can_enrich_diagnosis(await self._current(user_id), now, self.calendar.date_of(now))

    async def charge(self, user_id: UserId, cost: FeatureCost, now: datetime) -> None:
        async with self.uow as uow:
            # Service não faz commit: fora de uma transação de quem chama, a cobrança se perderia
            if not uow.joined:
                raise RuntimeError("TokenWallet.charge must be called inside the caller's unit of work.")
            subscription = await uow.subscriptions.lock(user_id)
            subscription.consume_tokens(cost, self.calendar.date_of(now))
            await uow.subscriptions.save(subscription)

    async def _current(self, user_id: UserId) -> Subscription:
        async with self.uow as uow:
            return await uow.subscriptions.get(user_id) or Subscription.free_for(user_id)
