from dataclasses import dataclass
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.exceptions import UserNotFoundError, PlantNotFoundError, ExternalServiceError
from src.domain.ports.user_repository import IUserRepository
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository
from src.domain.ports.plant_enricher import IPlantEnricher

@dataclass(frozen=True)
class EnrichPlantInputDTO:
    user_id: int
    species_id: int

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
        user = self.user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(dto.user_id)

        species = self.species_repo.get_by_id(dto.species_id)
        if not species:
            raise PlantNotFoundError(dto.species_id)

        # Política de Assinatura: Barra se não tiver 2 tokens para Análise Profunda
        SubscriptionPolicy.enforce_can_deep_analyze(user)

        # Verifica o Cache
        if not species.is_fully_enriched():
            # A planta é só um esqueleto. Vamos chamar o Gemini.
            # O 'enricher' já faz os 3 retries internamente e retorna um DTO tipado.
            try:
                enriched_data = self.enricher.enrich_botanical_data(species.scientific_name)
            except Exception as e:
                # Se após 3 tentativas o Gemini falhar ou der timeout, abortamos a transação.
                raise ExternalServiceError(message="Nossos botânicos de IA estão indisponíveis no momento. Tente novamente mais tarde.", code="AI_UNAVAILABLE")
            
            # Atualiza a Entidade Global com os novos VOs e salva
            species.apply_enrichment(enriched_data)
            self.species_repo.save(species)

        # Desconta os 2 tokens (independente de ter usado cache ou não)
        user.consume_deep_analysis_token()
        self.user_repo.save(user)

        # Retorna os dados completos (agora garantidamente enriquecidos)
        return {
            "scientific_name": species.scientific_name,
            "common_names": species.common_names,
            "description": species.description,
            "is_edible": species.is_edible,
            "care_schedule": {
                "watering_frequency_days": species.care_schedule.watering_frequency.days,
                "sunlight_level": species.care_schedule.sunlight_level,
                "ideal_soil": species.care_schedule.ideal_soil
            },
            "taxonomy": species.taxonomy
        }