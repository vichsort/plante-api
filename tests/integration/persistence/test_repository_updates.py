"""`save` de entidade já persistida atualiza a linha (antes fazia INSERT e violava a PK)."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog import PlantSpecies
from src.modules.catalog.adapters.persistence.repositories.plant_species import (
    PlantSpeciesRepository,
)


async def test_saving_new_species_maps_provider_entity_id(db_session: AsyncSession) -> None:
    repo = PlantSpeciesRepository(db_session)
    species = PlantSpecies.create_skeleton("Monstera deliciosa", genus="Monstera", provider_entity_id="ad11b3384dd5c143")

    await repo.save(species)
    await db_session.commit()

    loaded = await repo.get_by_scientific_name("Monstera deliciosa")
    assert loaded is not None
    assert loaded.id == species.id
    assert loaded.provider_entity_id == "ad11b3384dd5c143"
