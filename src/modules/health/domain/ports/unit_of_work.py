from src.modules.health.domain.ports.health_record_repository import (
    IHealthRecordRepository,
)
from src.shared.domain import IUnitOfWork


class IHealthUnitOfWork(IUnitOfWork):
    """Os diagnósticos dentro da transação (regras em `src.shared.domain.IUnitOfWork`)."""

    health_records: IHealthRecordRepository
