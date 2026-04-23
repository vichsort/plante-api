from dataclasses import dataclass
from datetime import datetime, timezone

from src.domain.entities.plant_species import PlantSpecies
from src.domain.entities.plant_reference_image import PlantReferenceImage, ImageSource
from src.domain.entities.user_plant import UserPlant
from src.domain.events.domain_events import PlantIdentifiedEvent
from src.domain.exceptions import UserNotFoundError, LowConfidenceError
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.image_storage import IImageStorage
from src.domain.ports.plant_identifier import IPlantIdentifier
from src.domain.ports.plant_reference_image_repository import IPlantReferenceImageRepository
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository
from src.domain.ports.user_repository import IUserRepository

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
        reference_image_repo: IPlantReferenceImageRepository,
        identifier: IPlantIdentifier,
        storage: IImageStorage,
        publisher: IDomainPublisher,
    ) -> None:
        self.user_repo = user_repo
        self.species_repo = species_repo
        self.reference_image_repo = reference_image_repo
        self.identifier = identifier
        self.storage = storage
        self.publisher = publisher

    async def execute(self, dto: IdentifyPlantInputDTO) -> dict:
        now = datetime.now(timezone.utc)

        # 1. Usuário existe?
        user = await self.user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(dto.user_id)

        # 2. Pode identificar? (limite diário Free vs Pro)
        SubscriptionPolicy.enforce_can_identify_plant(user)

        # 3. Chama o consensus engine (Kindwise + PlantNet)
        result = await self.identifier.identify(
            image_b64=dto.image_b64,
            lat=dto.latitude,
            lon=dto.longitude,
            country=dto.country,
            state=dto.state,
        )

        # 4. Confiança mínima não atingida — falha barata, sem I/O adicional
        if result.confidence.is_rejected():
            raise LowConfidenceError(confidence=result.confidence.value)

        # 5. Upload da foto do usuário → dataset futuro
        user_image_key = await self.storage.upload_identification_image(
            image_b64=dto.image_b64,
            scientific_name=result.scientific_name,
            confidence_value=result.confidence.value,
            user_id=user.id,
        )

        # 6. Re-hospeda imagens similares retornadas pelo Kindwise
        similar_image_keys: list[str] = []
        for external_url in result.similar_images_urls:
            key = await self.storage.download_and_rehost(
                external_url=external_url,
                scientific_name=result.scientific_name,
            )
            similar_image_keys.append(key)

        # 7. Persiste todas as imagens de referência
        user_reference = PlantReferenceImage(
            id=None,
            scientific_name=result.scientific_name,
            storage_key=user_image_key,
            source=ImageSource.USER_CONFIRMED,
            user_id=user.id,
            created_at=now,
        )
        await self.reference_image_repo.save(user_reference)

        for key in similar_image_keys:
            similar_reference = PlantReferenceImage(
                id=None,
                scientific_name=result.scientific_name,
                storage_key=key,
                source=ImageSource.KINDWISE_SIMILAR,
                user_id=None,
                created_at=now,
            )
            await self.reference_image_repo.save(similar_reference)

        # 8. Catálogo global: busca ou cria esqueleto da espécie
        species = await self.species_repo.get_by_scientific_name(result.scientific_name)
        if species is None:
            species = PlantSpecies.create_skeleton(
                scientific_name=result.scientific_name,
                family=result.family,
                common_names=result.common_names,
            )
            species = await self.species_repo.save(species)

        # 9. Cria a planta no jardim do usuário
        user_plant = await self._create_user_plant(species, user_image_key, now)

        # 10. Atualiza contadores na entidade do usuário
        is_first = user.garden_count == 0
        user.add_plant_to_garden()
        user.consume_identify_token()
        await self.publisher.publish(
            PlantIdentifiedEvent(..., is_first_plant=is_first)
        )

        # 11. Evento de domínio → listener de conquistas
        await self.publisher.publish(
            PlantIdentifiedEvent(
                user_id=user.id,
                species_id=species.id,
                is_first_plant=(user.garden_count == 1),
            )
        )

        return {
            "user_plant_id": user_plant.id,
            "scientific_name": species.scientific_name,
            "confidence": result.confidence.as_percentage(),
            "image_url": user_image_key,
            "needs_human_review": result.confidence.requires_human_review(),
        }

    async def _create_user_plant(
        self,
        species: PlantSpecies,
        image_key: str,
        now: datetime,
    ) -> UserPlant:
        """Isola a criação do UserPlant — candidato a use case próprio no futuro."""
        from src.domain.entities.user_plant import UserPlant
        from src.domain.ports.user_plant_repository import IUserPlantRepository

        user_plant = UserPlant.create_new(
            species_id=species.id,
            nickname=species.common_names[0] if species.common_names else species.scientific_name,
            primary_image_url=image_key,
            added_at=now,
        )
        return await self.user_plant_repo.save(user_plant)