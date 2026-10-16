from dataclasses import dataclass
from datetime import UTC, datetime

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
from src.domain.value_objects.local_calendar import LocalCalendar
from src.domain.value_objects.subscription_tier import FeatureCost


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
        calendar: LocalCalendar,
    ) -> None:
        self.uow = uow
        self.enricher = enricher
        self.calendar = calendar

    async def execute(self, dto: EnrichPlantInputDTO) -> PlantSpecies:
        now = datetime.now(UTC)
        today = self.calendar.date_of(now)
        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if not user:
                raise UserNotFoundError(user_id=dto.user_id)

            species = await uow.species.get_by_id(dto.species_id)
            if not species:
                raise SpeciesNotFoundError(dto.species_id)

            SubscriptionPolicy.enforce_can_deep_analyze(user, now, today)

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
            user.consume_tokens(FeatureCost.DEEP_ANALYSIS, today)
            await uow.users.save(user)
            await uow.commit()

        return species
