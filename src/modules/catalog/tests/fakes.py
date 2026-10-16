"""Dublê do `ISpeciesRegistry` para os testes de quem usa o catálogo (outros módulos e o código antigo)."""
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from src.modules.catalog.domain.entities.plant_species import PlantSpecies
from src.modules.catalog.domain.entities.reference_image import ImageSource
from src.modules.catalog.domain.services.species_registry import ISpeciesRegistry
from src.modules.catalog.domain.value_objects.ids import PlantSpeciesId


@dataclass
class FakeSpeciesRegistry(ISpeciesRegistry):
    """Catálogo em memória, pelo nome científico."""
    species: dict[str, PlantSpecies] = field(default_factory=dict)
    reference_images: list[tuple[str, str, ImageSource]] = field(default_factory=list)

    async def find_by_name(self, scientific_name: str) -> PlantSpecies | None:
        return self.species.get(scientific_name)

    async def get(self, species_id: PlantSpeciesId) -> PlantSpecies | None:
        return next((s for s in self.species.values() if s.id == species_id), None)

    async def register_identified(
        self,
        scientific_name: str,
        family: str | None,
        genus: str | None,
        common_names: tuple[str, ...],
        provider_entity_id: str | None,
        gbif_id: str | None,
    ) -> PlantSpecies:
        if scientific_name not in self.species:
            self.species[scientific_name] = PlantSpecies.create_skeleton(
                scientific_name, family, genus, common_names, provider_entity_id, gbif_id,
            )
        return self.species[scientific_name]

    async def add_reference_images(
        self, scientific_name: str, images: Sequence[tuple[str, ImageSource]], at: datetime,
    ) -> None:
        self.reference_images += [(scientific_name, key, source) for key, source in images]

    async def save(self, species: PlantSpecies) -> PlantSpecies:
        self.species[species.scientific_name] = species
        return species
