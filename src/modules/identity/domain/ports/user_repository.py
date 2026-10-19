from abc import ABC, abstractmethod

from src.modules.identity.domain.entities.user import User
from src.shared.domain import UserId


class IUserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def delete(self, user_id: UserId) -> None:
        """
        Deletes the account for good. The database takes the user's data along (`CASCADE`); the
        training data has no link to the user and stays.
        """
        ...