from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.domain.entities.user import User
from src.domain.events.domain_events import SubscriptionUpgradedEvent
from src.domain.exceptions import UserNotFoundError
from src.domain.ports.unit_of_work import IUnitOfWork
from src.shared.domain import IDomainPublisher, UserId


@dataclass(frozen=True)
class UpgradeSubscriptionInputDTO:
    user_id: UserId
    plan_duration_days: int

class UpgradeSubscriptionUseCase:
    raises = (UserNotFoundError,)

    def __init__(
        self,
        uow: IUnitOfWork,
        publisher: IDomainPublisher,
    ) -> None:
        self.uow = uow
        self.publisher = publisher

    async def execute(self, dto: UpgradeSubscriptionInputDTO) -> User:
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=dto.plan_duration_days)

        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if not user:
                raise UserNotFoundError(user_id=dto.user_id)

            user.upgrade_to_pro(expires_at=expires_at, current_time=now)
            await uow.users.save(user)
            await uow.commit()

        await self.publisher.publish(SubscriptionUpgradedEvent.create(
            user_id=user.id,
            plan_name="PRO",
            expires_at=expires_at,
        ))

        return user
