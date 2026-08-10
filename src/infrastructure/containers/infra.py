from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.persistence.session import build_session_factory


def build_session_instance(session_factory: async_sessionmaker[AsyncSession]) -> AsyncSession:
    return session_factory()

class InfraContainer(containers.DeclarativeContainer):
    settings = providers.Dependency()

    session_factory = providers.Singleton(
        build_session_factory,
        settings=settings,
    )

    session = providers.Factory(
        build_session_instance,
        session_factory=session_factory,
    )