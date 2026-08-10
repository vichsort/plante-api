from dataclasses import dataclass
from typing import Any

from src.domain.exceptions import (
    ExternalServiceError,
    PlantNotFoundError,
    UserNotFoundError,
)
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.plant_enricher import IPlantEnricher
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository
from src.domain.ports.user_repository import IUserRepository


@dataclass(frozen=True)
class EnrichPlantInputDTO:
    user_id: Any
    species_id: Any

class EnrichPlantSpeciesUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        species_repo: IPlantSpeciesRepository,
        enricher: IPlantEnricher
    ):
        self.user_repo = user_repo
        self.species_repo = species_repo
        self.enricher = enricher

    async def execute(self, dto: EnrichPlantInputDTO) -> dict:
        user = await self.user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(user_id=dto.user_id)

        species = await self.species_repo.get_by_id(dto.species_id)
        if not species:
            raise PlantNotFoundError(dto.species_id)

        SubscriptionPolicy.enforce_can_deep_analyze(user)

        if not species.is_enriched:
            try:
                await self.enricher.enrich_species(species.scientific_name)
            except Exception:
                raise ExternalServiceError(message="Nossos botânicos de IA estão indisponíveis no momento. Tente novamente mais tarde.")
            
            await self.species_repo.save(species)

        user.consume_deep_analysis_token()
        await self.user_repo.save(user)

        return {
            "scientific_name": species.scientific_name,
            "common_names": list(species.common_names),
            "is_edible": species.is_edible,
            "habitat": species.habitat,
        }