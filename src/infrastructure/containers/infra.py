from dependency_injector import containers, providers
from src.adapters.persistence.session import build_session_factory
from sqlalchemy.ext.asyncio import AsyncSession

class InfraContainer(containers.DeclarativeContainer):
    settings = providers.Dependency()
    
    session_factory = providers.Singleton(
        build_session_factory,
        settings=settings,
    )

    session = providers.Resource(
        AsyncSession,
        bind=session_factory,
    )