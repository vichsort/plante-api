from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.ports.unit_of_work import IQuotaUnitOfWork
from src.shared.domain import UserId, UserNotFoundError

MAX_GRANT_DAYS = 365


@dataclass(frozen=True)
class GrantExtendedQuotaInputDTO:
    user_id: UserId
    days: int


class GrantExtendedQuotaUseCase:
    """
    The maintainer grants the extended quota, for free and with a deadline (a school, a researcher,
    an NGO). There is no HTTP route: it runs from `src.bootstrap.quota_admin`, on the server.
    """
    raises = (UserNotFoundError,)

    def __init__(self, uow: IQuotaUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: GrantExtendedQuotaInputDTO) -> Quota:
        if not 1 <= dto.days <= MAX_GRANT_DAYS:
            raise ValueError(f"days must be between 1 and {MAX_GRANT_DAYS}.")
        now = datetime.now(UTC)
        async with self.uow as uow:
            quota = await uow.quotas.lock(dto.user_id)
            quota.grant_extended(expires_at=now + timedelta(days=dto.days), current_time=now)
            await uow.quotas.save(quota)
            await uow.commit()
        return quota
