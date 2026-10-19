from src.modules.quota.domain.ports.repository import IQuotaRepository
from src.shared.domain import IUnitOfWork


class IQuotaUnitOfWork(IUnitOfWork):
    """Planos e cotas dentro da transação (regras em `src.shared.domain.IUnitOfWork`)."""

    quotas: IQuotaRepository
