from abc import ABC, abstractmethod

from src.modules.identity.domain.exceptions import TermsNotAcceptedError
from src.modules.identity.domain.ports.unit_of_work import IIdentityUnitOfWork
from src.modules.identity.domain.value_objects.email import normalize_email
from src.modules.identity.domain.value_objects.terms import Terms
from src.modules.identity.domain.value_objects.user_location import UserLocation
from src.shared.domain import UserId, UserNotFoundError


class IUserDirectory(ABC):
    """
    O que os outros módulos podem saber do usuário, sem ver a conta (credenciais e e-mail ficam
    aqui). Lê dentro da transação de quem chama, se houver uma aberta.
    """

    @abstractmethod
    async def id_by_email(self, email: str) -> UserId:
        """
        For the maintainer's tools, which find the user by the email they know (the email itself
        never leaves this module). Raises `UserNotFoundError` if no account has it.
        """
        ...

    @abstractmethod
    async def ensure_exists(self, user_id: UserId) -> None:
        """Lança `UserNotFoundError` se o usuário não tem conta."""
        ...

    @abstractmethod
    async def region_of(self, user_id: UserId) -> UserLocation:
        """O país e o estado do perfil. Lança `UserNotFoundError` se o usuário não tem conta."""
        ...

    @abstractmethod
    async def ensure_accepted_terms(self, user_id: UserId) -> None:
        """
        Before anything that sends the user's photo out (providers, training dataset). Raises
        `TermsNotAcceptedError` if the user has not accepted the terms in force, and
        `UserNotFoundError` if there is no account.
        """
        ...


class UserDirectory(IUserDirectory):
    def __init__(self, uow: IIdentityUnitOfWork, terms: Terms) -> None:
        self.uow = uow
        self.terms = terms

    async def id_by_email(self, email: str) -> UserId:
        async with self.uow as uow:
            user = await uow.users.get_by_email(normalize_email(email))
        if user is None:
            raise UserNotFoundError("No account has this email.")
        return user.id

    async def ensure_exists(self, user_id: UserId) -> None:
        await self.region_of(user_id)

    async def region_of(self, user_id: UserId) -> UserLocation:
        async with self.uow as uow:
            user = await uow.users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        return user.location

    async def ensure_accepted_terms(self, user_id: UserId) -> None:
        async with self.uow as uow:
            user = await uow.users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id=user_id)
        if not user.has_accepted(self.terms.version):
            raise TermsNotAcceptedError(self.terms.version)
