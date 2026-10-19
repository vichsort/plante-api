from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.ports.unit_of_work import IQuotaUnitOfWork
from src.shared.domain import UserId, UserNotFoundError


class RevokeExtendedQuotaUseCase:
    """The maintainer takes the extended quota back before its deadline (see `GrantExtendedQuotaUseCase`)."""
    raises = (UserNotFoundError,)

    def __init__(self, uow: IQuotaUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, user_id: UserId) -> Quota:
        async with self.uow as uow:
            quota = await uow.quotas.lock(user_id)
            quota.revoke_extended()
            await uow.quotas.save(quota)
            await uow.commit()
        return quota
