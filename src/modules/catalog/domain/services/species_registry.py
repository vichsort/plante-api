from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from src.modules.catalog.domain.entities.plant_species import PlantSpecies
from src.modules.catalog.domain.entities.reference_image import (
    ImageSource,
    PlantReferenceImage,
)
from src.modules.catalog.domain.ports.unit_of_work import ICatalogUnitOfWork
from src.modules.catalog.domain.value_objects.ids import (
    PlantSpeciesId,
    ReferenceImageId,
)


class ISpeciesRegistry(ABC):
    """
    O catálogo para os outros módulos. Escritas rodam **dentro da transação de quem chama** (a
    espécie e as imagens de referência entram junto com a identificação, ou nada entra); leituras
    funcionam também fora de uma transação.
    """

    @abstractmethod
    async def find_by_name(self, scientific_name: str) -> PlantSpecies | None:
        ...

    @abstractmethod
    async def get(self, species_id: PlantSpeciesId) -> PlantSpecies | None:
        ...

    @abstractmethod
    async def register_identified(
        self,
        scientific_name: str,
        family: str | None,
        genus: str | None,
        common_names: tuple[str, ...],
        provider_entity_id: str | None,
        gbif_id: str | None,
    ) -> PlantSpecies:
        """A espécie que um provedor apontou: a já cadastrada, ou um esqueleto novo (sem enriquecimento)."""
        ...

    @abstractmethod
    async def add_reference_images(
        self, scientific_name: str, images: Sequence[tuple[str, ImageSource]], at: datetime,
    ) -> None:
        """Imagens de referência (dos provedores, não do usuário), já rehospedadas: chave + origem."""
        ...

    @abstractmethod
    async def save(self, species: PlantSpecies) -> PlantSpecies:
        ...


class SpeciesRegistry(ISpeciesRegistry):
    def __init__(self, uow: ICatalogUnitOfWork) -> None:
        self.uow = uow

    async def find_by_name(self, scientific_name: str) -> PlantSpecies | None:
        async with self.uow as uow:
            return await uow.species.get_by_scientific_name(scientific_name)

    async def get(self, species_id: PlantSpeciesId) -> PlantSpecies | None:
        async with self.uow as uow:
            return await uow.species.get_by_id(species_id)

    async def register_identified(
        self,
        scientific_name: str,
        family: str | None,
        genus: str | None,
        common_names: tuple[str, ...],
        provider_entity_id: str | None,
        gbif_id: str | None,
    ) -> PlantSpecies:
        async with self.uow as uow:
            _require_callers_transaction(uow)
            existing = await uow.species.get_by_scientific_name(scientific_name)
            if existing is not None:
                return existing
            return await uow.species.save(PlantSpecies.create_skeleton(
                scientific_name=scientific_name,
                family=family,
                genus=genus,
                common_names=common_names,
                provider_entity_id=provider_entity_id,
                gbif_id=gbif_id,
            ))

    async def add_reference_images(
        self, scientific_name: str, images: Sequence[tuple[str, ImageSource]], at: datetime,
    ) -> None:
        async with self.uow as uow:
            _require_callers_transaction(uow)
            for key, source in images:
                await uow.reference_images.save(PlantReferenceImage(
                    id=ReferenceImageId(uuid4()),
                    scientific_name=scientific_name,
                    storage_key=key,
                    source=source,
                    user_id=None,
                    created_at=at,
                ))

    async def save(self, species: PlantSpecies) -> PlantSpecies:
        async with self.uow as uow:
            _require_callers_transaction(uow)
            return await uow.species.save(species)


def _require_callers_transaction(uow: ICatalogUnitOfWork) -> None:
    # Service não faz commit: escrita fora de uma transação de quem chama se perderia em silêncio
    if not uow.joined:
        raise RuntimeError("SpeciesRegistry writes must run inside the caller's unit of work.")
