from src.modules.training.domain.ports.repository import ITrainingRepository
from src.shared.domain import IUnitOfWork


class ITrainingUnitOfWork(IUnitOfWork):
    """O dataset dentro da transação de quem grava (regras em `src.shared.domain.IUnitOfWork`)."""

    training: ITrainingRepository
