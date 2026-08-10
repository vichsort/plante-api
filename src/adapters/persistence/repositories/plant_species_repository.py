from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.mappers.plant_species_mapper import PlantSpeciesMapper
from src.adapters.persistence.models.plant_species_model import PlantSpeciesModel
from src.domain.entities.plant_species import EnrichmentStatus, PlantSpecies
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository


class PlantSpeciesRepository(IPlantSpeciesRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, species: PlantSpecies) -> PlantSpecies:
        model = PlantSpeciesMapper.to_model(species)
        self._session.add(model)
        await self._session.flush()
        return PlantSpeciesMapper.to_domain(model)

    async def get_by_id(self, species_id: Any) -> PlantSpecies | None:
        stmt = select(PlantSpeciesModel).where(PlantSpeciesModel.id == species_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return PlantSpeciesMapper.to_domain(model) if model else None

    async def get_by_scientific_name(self, scientific_name: str) -> PlantSpecies | None:
        stmt = select(PlantSpeciesModel).where(
            PlantSpeciesModel.scientific_name == scientific_name
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return PlantSpeciesMapper.to_domain(model) if model else None

    async def update_enrichment_status(
        self,
        scientific_name: str,
        status: EnrichmentStatus,
    ) -> None:
        values: dict[str, Any] = {"enrichment_status": status.value}
        if status == EnrichmentStatus.ENRICHED:
            values["enriched_at"] = datetime.now(UTC)
        stmt = (
            update(PlantSpeciesModel)
            .where(PlantSpeciesModel.scientific_name == scientific_name)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def list_pending_enrichment(self, limit: int = 50) -> list[PlantSpecies]:
        stmt = (
            select(PlantSpeciesModel)
            .where(PlantSpeciesModel.enrichment_status == EnrichmentStatus.PENDING.value)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [PlantSpeciesMapper.to_domain(m) for m in result.scalars().all()]