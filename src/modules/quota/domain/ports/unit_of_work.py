from src.modules.quota.domain.ports.repository import IQuotaRepository
from src.shared.domain import IUnitOfWork


class IQuotaUnitOfWork(IUnitOfWork):
    """Quotas inside the transaction (regras em `src.shared.domain.IUnitOfWork`)."""

    quotas: IQuotaRepository
