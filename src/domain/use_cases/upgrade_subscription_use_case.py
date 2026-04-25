from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from src.domain.exceptions import UserNotFoundError
from src.domain.ports.user_repository import IUserRepository
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.events.domain_events import SubscriptionUpgradedEvent

@dataclass(frozen=True)
class UpgradeSubscriptionInputDTO:
    user_id: int
    plan_duration_days: int

class UpgradeSubscriptionUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        publisher: IDomainPublisher,
    ) -> None:
        self.user_repo = user_repo
        self.publisher = publisher

    async def execute(self, dto: UpgradeSubscriptionInputDTO) -> dict:
        user = await self.user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(dto.user_id)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=dto.plan_duration_days)

        user.upgrade_to_pro(expires_at=expires_at)
        await self.user_repo.save(user)

        event = SubscriptionUpgradedEvent.create(
            user_id=user.id,
            plan_name="PRO",
            expires_at=expires_at,
        )
        self.publisher.publish(event)

        return {
            "user_id": user.id,
            "new_tier": "PRO",
            "expires_at": expires_at.isoformat(),
            "message": "Parabéns! Você agora é um membro Premium do PlantE.",
        }