from src.modules.identification.domain.ports.identification_repository import (
    IIdentificationRepository,
)
from src.shared.domain import IUnitOfWork


class IIdentificationUnitOfWork(IUnitOfWork):
    """As identificações dentro da transação (regras em `src.shared.domain.IUnitOfWork`)."""

    identifications: IIdentificationRepository
