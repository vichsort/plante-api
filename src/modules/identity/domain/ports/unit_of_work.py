from src.modules.identity.domain.ports.user_repository import IUserRepository
from src.shared.domain import IUnitOfWork


class IIdentityUnitOfWork(IUnitOfWork):
    """As contas dentro da transação (regras em `src.shared.domain.IUnitOfWork`)."""

    users: IUserRepository
