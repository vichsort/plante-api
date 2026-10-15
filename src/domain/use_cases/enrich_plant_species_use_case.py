from dataclasses import dataclass

from src.domain.entities.plant_species import PlantSpecies
from src.domain.exceptions import (
    ExternalServiceError,
    SpeciesNotFoundError,
    SubscriptionRequiredError,
    UserNotFoundError,
)
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.plant_enricher import IPlantEnricher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import PlantSpeciesId, UserId


@dataclass(frozen=True)
class EnrichPlantInputDTO:
    user_id: UserId
    species_id: PlantSpeciesId

class EnrichPlantSpeciesUseCase:
    raises = (
        ExternalServiceError,
        SpeciesNotFoundError,
        SubscriptionRequiredError,
        UserNotFoundError,
    )

    def __init__(
        self,
        uow: IUnitOfWork,
        enricher: IPlantEnricher,
    ) -> None:
        self.uow = uow
        self.enricher = enricher

    async def execute(self, dto: EnrichPlantInputDTO) -> PlantSpecies:
        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if not user:
                raise UserNotFoundError(user_id=dto.user_id)

            species = await uow.species.get_by_id(dto.species_id)
            if not species:
                raise SpeciesNotFoundError(dto.species_id)

            SubscriptionPolicy.enforce_can_deep_analyze(user)

        # Chamada lenta fora da transação
        if not species.is_enriched:
            try:
                await self.enricher.enrich_species(species.scientific_name)
            except Exception:
                raise ExternalServiceError(message="Nossos botânicos de IA estão indisponíveis no momento. Tente novamente mais tarde.")

        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if not user:
                raise UserNotFoundError(user_id=dto.user_id)
            if not species.is_enriched:
                await uow.species.save(species)
            user.consume_deep_analysis_token()
            await uow.users.save(user)
            await uow.commit()

        return species
