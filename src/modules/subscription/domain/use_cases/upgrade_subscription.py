from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.modules.subscription.domain.entities.subscription import Subscription
from src.modules.subscription.domain.events import SubscriptionUpgradedEvent
from src.modules.subscription.domain.ports.unit_of_work import ISubscriptionUnitOfWork
from src.shared.domain import IDomainPublisher, UserId, UserNotFoundError


@dataclass(frozen=True)
class UpgradeSubscriptionInputDTO:
    user_id: UserId
    plan_duration_days: int


class UpgradeSubscriptionUseCase:
    """Hoje: upgrade sem pagamento (o plano é demonstrativo; a cota de tokens é que é regra de verdade)."""

    raises = (UserNotFoundError,)  # do repositório, ao travar a assinatura de quem não tem conta

    def __init__(self, uow: ISubscriptionUnitOfWork, publisher: IDomainPublisher) -> None:
        self.uow = uow
        self.publisher = publisher

    async def execute(self, dto: UpgradeSubscriptionInputDTO) -> Subscription:
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=dto.plan_duration_days)

        async with self.uow as uow:
            subscription = await uow.subscriptions.lock(dto.user_id)
            subscription.upgrade_to_pro(expires_at=expires_at, current_time=now)
            await uow.subscriptions.save(subscription)
            await uow.commit()

        await self.publisher.publish(SubscriptionUpgradedEvent.create(
            user_id=dto.user_id,
            plan_name=subscription.tier.plan_name,
            expires_at=expires_at,
        ))
        return subscription
