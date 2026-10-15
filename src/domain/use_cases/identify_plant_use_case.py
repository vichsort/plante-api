from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from src.domain.entities.care_schedule import CareSchedule, CareType
from src.domain.entities.plant_identification_sample import PlantIdentificationSample
from src.domain.entities.plant_reference_image import PlantReferenceImage
from src.domain.entities.plant_species import PlantSpecies
from src.domain.entities.user_plant import (
    IdentificationSource,
    IdentificationStatus,
    UserPlant,
)
from src.domain.events.domain_events import PlantIdentifiedEvent
from src.domain.exceptions import (
    ExternalServiceError,
    InvalidImageError,
    LowConfidenceError,
    PlantLimitExceededError,
    SubscriptionRequiredError,
    UserNotFoundError,
)
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.identification_sample_repository import (
    IIdentificationSampleRepository,
)
from src.domain.ports.image_storage import IImageStorage
from src.domain.ports.plant_identifier import IPlantIdentifier
from src.domain.ports.plant_reference_image_repository import (
    IPlantReferenceImageRepository,
)
from src.domain.ports.plant_species_repository import IPlantSpeciesRepository
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.user_repository import IUserRepository
from src.domain.value_objects.care_interval import CareInterval
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.ids import (
    IdentificationSampleId,
    ReferenceImageId,
    UserId,
    UserPlantId,
)
from src.domain.value_objects.sources import IdentificationOrigin


@dataclass(frozen=True)
class IdentifyPlantInputDTO:
    user_id: UserId
    image_bytes: bytes
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class IdentifyPlantOutput:
    user_plant_id: UserPlantId
    sample_id: IdentificationSampleId
    scientific_name: str
    confidence: ConfidenceScore
    image_url: str
    needs_human_review: bool


# Origem da identificação -> como a planta registra quem a identificou
_IDENTIFICATION_SOURCE: dict[IdentificationOrigin, IdentificationSource] = {
    "kindwise": IdentificationSource.KINDWISE,
    "plantnet": IdentificationSource.PLANTNET,
    "consensus": IdentificationSource.CONSENSUS,
    "consensus_partial": IdentificationSource.CONSENSUS,
}


class IdentifyPlantUseCase:
    raises = (
        ExternalServiceError,
        InvalidImageError,
        LowConfidenceError,
        PlantLimitExceededError,
        SubscriptionRequiredError,
        UserNotFoundError,
    )

    def __init__(
        self,
        user_repo: IUserRepository,
        species_repo: IPlantSpeciesRepository,
        user_plant_repo: IUserPlantRepository,
        reference_image_repo: IPlantReferenceImageRepository,
        sample_repo: IIdentificationSampleRepository,
        plant_identifier: IPlantIdentifier,
        storage: IImageStorage,
        publisher: IDomainPublisher,
    ) -> None:
        self.user_repo = user_repo
        self.species_repo = species_repo
        self.user_plant_repo = user_plant_repo
        self.reference_image_repo = reference_image_repo
        self.sample_repo = sample_repo
        self.plant_identifier = plant_identifier
        self.storage = storage
        self.publisher = publisher

    async def execute(self, dto: IdentifyPlantInputDTO) -> IdentifyPlantOutput:
        now = datetime.now(UTC)

        user = await self.user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(user_id=dto.user_id)

        SubscriptionPolicy.enforce_can_identify_plant(user)

        result = await self.plant_identifier.identify(
            image_bytes=dto.image_bytes,
            latitude=dto.latitude,
            longitude=dto.longitude,
        )

        if result.confidence.is_rejected():
            raise LowConfidenceError(confidence=result.confidence.value)

        user_image_key = await self.storage.upload_identification_image(
            image_bytes=dto.image_bytes,
            scientific_name=result.scientific_name,
            confidence_value=result.confidence.value,
            user_id=user.id,
        )

        for similar in result.similar_images:
            key = await self.storage.download_and_rehost(
                external_url=similar.url,
                scientific_name=result.scientific_name,
            )
            await self.reference_image_repo.save(PlantReferenceImage(
                id=ReferenceImageId(uuid4()),
                scientific_name=result.scientific_name,
                storage_key=key,
                source=similar.source,
                user_id=None,
                created_at=now,
            ))

        species = await self.species_repo.get_by_scientific_name(result.scientific_name)
        if species is None:
            species = PlantSpecies.create_skeleton(
                scientific_name=result.scientific_name,
                family=result.family,
                genus=result.genus,
                common_names=result.common_names,
                provider_entity_id=result.provider_entity_id,
                gbif_id=result.gbif_id,
            )
            species = await self.species_repo.save(species)

        care_schedule = CareSchedule(
            care_type=CareType.WATER,
            interval=CareInterval(days=7),
            is_active=True,
            created_at=now,
        )

        user_plant = await self.user_plant_repo.save(UserPlant(
            id=UserPlantId(uuid4()),
            user_id=user.id,
            scientific_name=result.scientific_name,
            identification_confidence=result.confidence.value,
            identification_source=_IDENTIFICATION_SOURCE[result.source],
            status=IdentificationStatus.IDENTIFIED,
            care_schedule=care_schedule,
            primary_image_url=user_image_key,
            added_at=now,
        ))

        sample = await self.sample_repo.save(PlantIdentificationSample.create(
            scientific_name=result.scientific_name,
            species_id=species.id,
            user_image_key=user_image_key,
            identification_confidence=result.confidence.value,
            identification_source=result.source,
            raw_response=result.raw_response,
            user_id=user.id,
            created_at=now,
        ))

        user.consume_identify_token()
        await self.user_repo.save(user)

        await self.publisher.publish(PlantIdentifiedEvent.create(
            user_id=user.id,
            species_id=species.id,
            is_first_plant=False,
        ))

        return IdentifyPlantOutput(
            user_plant_id=user_plant.id,
            sample_id=sample.id,
            scientific_name=species.scientific_name,
            confidence=result.confidence,
            image_url=user_image_key,
            needs_human_review=result.confidence.requires_human_review(),
        )