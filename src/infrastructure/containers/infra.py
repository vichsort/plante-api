from dependency_injector import containers, providers

from src.adapters.persistence.session import build_engine, build_session_factory
from src.adapters.persistence.unit_of_work import SqlAlchemyUnitOfWork
from src.infrastructure.settings import Settings


class InfraContainer(containers.DeclarativeContainer):
    settings: providers.Dependency[Settings] = providers.Dependency()

    engine = providers.Singleton(
        build_engine,
        database_url=settings.provided.database_url,
        echo=settings.provided.debug,
    )

    session_factory = providers.Singleton(
        build_session_factory,
        engine=engine,
    )

    # Um por use case: cada `async with` abre uma sessão própria e a fecha no fim
    unit_of_work = providers.Factory(
        SqlAlchemyUnitOfWork,
        session_factory=session_factory,
    )
