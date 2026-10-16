from abc import ABC, abstractmethod

from src.modules.identity.domain.ports.unit_of_work import IIdentityUnitOfWork
from src.modules.identity.domain.value_objects.user_location import UserLocation
from src.shared.domain import UserId, UserNotFoundError


class IUserDirectory(ABC):
    """
    O que os outros módulos podem saber do usuário, sem ver a conta (credenciais e e-mail ficam
    aqui). Lê dentro da transação de quem chama, se houver uma aberta.
    """

    @abstractmethod
    async def ensure_exists(self, user_id: UserId) -> None:
        """Lança `UserNotFoundError` se o usuário não tem conta."""
        ...

    @abstractmethod
    async def region_of(self, user_id: UserId) -> UserLocation:
        """O país e o estado do perfil. Lança `UserNotFoundError` se o usuário não tem conta."""
        ...


class UserDirectory(IUserDirectory):
    def __init__(self, uow: IIdentityUnitOfWork) -> None:
        self.uow = uow

    async def ensure_exists(self, user_id: UserId) -> None:
        await self.region_of(user_id)

    async def region_of(self, user_id: UserId) -> UserLocation:
        async with self.uow as uow:
            user = await uow.users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return user.location
