from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.domain.entities.user import User
from src.domain.events.domain_events import SubscriptionUpgradedEvent
from src.domain.exceptions import UserNotFoundError
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.user_repository import IUserRepository
from src.domain.value_objects.ids import UserId


@dataclass(frozen=True)
class UpgradeSubscriptionInputDTO:
    user_id: UserId
    plan_duration_days: int

class UpgradeSubscriptionUseCase:
    raises = (UserNotFoundError,)

    def __init__(
        self,
        user_repo: IUserRepository,
        publisher: IDomainPublisher,
    ) -> None:
        self.user_repo = user_repo
        self.publisher = publisher

    async def execute(self, dto: UpgradeSubscriptionInputDTO) -> User:
        user = await self.user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(user_id=dto.user_id)

        now = datetime.now(UTC)
        expires_at = now + timedelta(days=dto.plan_duration_days)

        user.upgrade_to_pro(expires_at=expires_at, current_time=now)
        await self.user_repo.save(user)

        event = SubscriptionUpgradedEvent.create(
            user_id=user.id,
            plan_name="PRO",
            expires_at=expires_at,
        )
        await self.publisher.publish(event)

        return user