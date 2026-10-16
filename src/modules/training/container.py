from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.training.adapters.persistence.unit_of_work import (
    SqlAlchemyTrainingUnitOfWork,
)
from src.modules.training.domain.services.recorder import TrainingRecorder


class TrainingContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyTrainingUnitOfWork, session_factory=session_factory)
    recorder = providers.Factory(TrainingRecorder, uow=unit_of_work)
