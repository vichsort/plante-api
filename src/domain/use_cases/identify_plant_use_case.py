from dataclasses import dataclass
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.exceptions import UserNotFoundError, LowConfidenceError
from src.domain.entities.user import User
from src.domain.entities.user_plant import UserPlant
from src.domain.entities.plant_species import PlantSpecies
from src.domain.ports.user_repository import IUserRepository
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository
from src.domain.ports.plant_identifier import IPlantIdentifier
from src.domain.ports.image_storage import IImageStorage
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.events.domain_events import PlantIdentifiedEvent

@dataclass(frozen=True)
class IdentifyPlantInputDTO:
    user_id: int
    image_b64: str
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    state: str | None = None


class IdentifyPlantUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        species_repo: IPlantSpeciesRepository,
        identifier: IPlantIdentifier,
        storage: IImageStorage,
        publisher: IDomainPublisher
    ):
        self.user_repo = user_repo
        self.species_repo = species_repo
        self.identifier = identifier
        self.storage = storage
        self.publisher = publisher

    def execute(self, dto: IdentifyPlantInputDTO) -> dict:
        user = self.user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(dto.user_id)

        # Política de Assinatura: Barra imediatamente se não puder adicionar/pagar
        SubscriptionPolicy.enforce_can_identify_plant(user)

        # chama as IAs de cruza
        identification_result = self.identifier.identify(
            image_b64=dto.image_b64, 
            lat=dto.latitude, 
            lon=dto.longitude,
            country=dto.country,
            state=dto.state
        )

        # Avalia a Confiança antes de prosseguir e gastar recursos do sistema
        if identification_result.confidence.is_rejected():
            # Falhou. Não descontamos o token, não salvamos no bucket.
            raise LowConfidenceError(confidence=identification_result.confidence.value)

        # Sucesso na identificação! Agora salvamos a foto no nosso Bucket (O Dataset do Futuro)
        # Ex: s3://plante-dataset/training_data/monstera_deliciosa/0.95_user1_1713876000.jpg
        permanent_image_url = self.storage.upload_identification_image(
            image_b64=dto.image_b64,
            scientific_name=identification_result.scientific_name,
            confidence_value=identification_result.confidence.value,
            user_id=user.id
        )

        # Catálogo Global: Busca a espécie ou cria o "esqueleto" vazio para o Gemini preencher depois
        species = self.species_repo.get_by_scientific_name(identification_result.scientific_name)
        if not species:
            species = PlantSpecies.create_skeleton(
                scientific_name=identification_result.scientific_name,
                family=identification_result.family,
                common_names=identification_result.common_names
            )
            self.species_repo.save(species)

        # Jardim do Usuário: Cria a planta pessoal
        user_plant = UserPlant.create_new(
            species_id=species.id,
            nickname=identification_result.common_names[0] if identification_result.common_names else species.scientific_name,
            primary_image_url=permanent_image_url
        )

        # Adiciona a planta e desconta o token
        user.add_plant_to_garden(user_plant)
        user.consume_identify_token()

        # Salva o estado atualizado do usuário (e da planta por cascata)
        self.user_repo.save(user)

        # Despacha o Evento para que os Listeners concedam as Conquistas (Achievements)
        event = PlantIdentifiedEvent(user_id=user.id, species_id=species.id, is_first_plant=(user.garden_count == 1))
        self.publisher.publish(event)

        # Retorna os dados para a API montar o JSON de resposta
        return {
            "user_plant_id": user_plant.id,
            "scientific_name": species.scientific_name,
            "confidence": identification_result.confidence.as_percentage(),
            "image_url": permanent_image_url,
            "needs_human_review": identification_result.confidence.requires_human_review()
        }