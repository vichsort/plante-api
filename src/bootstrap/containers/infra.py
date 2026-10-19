from dependency_injector import containers, providers

from src.bootstrap.settings import Settings
from src.shared.adapters import build_engine, build_session_factory


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
