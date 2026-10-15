from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.persistence.session import build_engine, build_session_factory
from src.infrastructure.settings import Settings


def build_session_instance(session_factory: async_sessionmaker[AsyncSession]) -> AsyncSession:
    return session_factory()


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

    session = providers.Factory(
        build_session_instance,
        session_factory=session_factory,
    )