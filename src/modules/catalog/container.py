from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.catalog.adapters.gemini.enricher import GeminiSpeciesEnricher
from src.modules.catalog.adapters.persistence.unit_of_work import (
    SqlAlchemyCatalogUnitOfWork,
)
from src.modules.catalog.domain.services.species_registry import SpeciesRegistry


class CatalogContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()
    gemini_api_key: providers.Dependency[str | None] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyCatalogUnitOfWork, session_factory=session_factory)
    registry = providers.Factory(SpeciesRegistry, uow=unit_of_work)
    species_enricher = providers.Singleton(GeminiSpeciesEnricher, api_key=gemini_api_key)
