from src.modules.subscription.domain.ports.repository import ISubscriptionRepository
from src.shared.domain import IUnitOfWork


class ISubscriptionUnitOfWork(IUnitOfWork):
    """Planos e cotas dentro da transação (regras em `src.shared.domain.IUnitOfWork`)."""

    subscriptions: ISubscriptionRepository
