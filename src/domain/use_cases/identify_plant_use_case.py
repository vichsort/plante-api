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
from src.domain.ports.image_sanitizer import IImageSanitizer
from src.domain.ports.image_storage import IImageStorage
from src.domain.ports.plant_identifier import IPlantIdentifier
from src.domain.ports.unit_of_work import IUnitOfWork
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
        uow: IUnitOfWork,
        sanitizer: IImageSanitizer,
        plant_identifier: IPlantIdentifier,
        storage: IImageStorage,
        publisher: IDomainPublisher,
    ) -> None:
        self.uow = uow
        self.sanitizer = sanitizer
        self.plant_identifier = plant_identifier
        self.storage = storage
        self.publisher = publisher

    async def execute(self, dto: IdentifyPlantInputDTO) -> IdentifyPlantOutput:
        now = datetime.now(UTC)

        # 1. Leitura curta: a transação não fica aberta durante as chamadas à IA e ao S3
        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)
            SubscriptionPolicy.enforce_can_identify_plant(user)

        # 2. Serviços externos, só com a foto já sem metadados (GPS, aparelho, data)
        image_bytes = self.sanitizer.sanitize(dto.image_bytes)
        result = await self.plant_identifier.identify(
            image_bytes=image_bytes,
            latitude=dto.latitude,
            longitude=dto.longitude,
        )

        if result.confidence.is_rejected():
            raise LowConfidenceError(confidence=result.confidence.value)

        user_image_key = await self.storage.upload_identification_image(
            image_bytes=image_bytes,
            scientific_name=result.scientific_name,
            confidence_value=result.confidence.value,
            user_id=dto.user_id,
        )

        rehosted = [
            (await self.storage.download_and_rehost(
                external_url=similar.url,
                scientific_name=result.scientific_name,
            ), similar.source)
            for similar in result.similar_images
        ]

        # 3. Escrita numa transação só; o usuário é relido para cobrar o token sobre o estado atual
        async with self.uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if user is None:
                raise UserNotFoundError(user_id=dto.user_id)

            for key, source in rehosted:
                await uow.reference_images.save(PlantReferenceImage(
                    id=ReferenceImageId(uuid4()),
                    scientific_name=result.scientific_name,
                    storage_key=key,
                    source=source,
                    user_id=None,
                    created_at=now,
                ))

            species = await uow.species.get_by_scientific_name(result.scientific_name)
            if species is None:
                species = await uow.species.save(PlantSpecies.create_skeleton(
                    scientific_name=result.scientific_name,
                    family=result.family,
                    genus=result.genus,
                    common_names=result.common_names,
                    provider_entity_id=result.provider_entity_id,
                    gbif_id=result.gbif_id,
                ))

            care_schedule = CareSchedule(
                care_type=CareType.WATER,
                interval=CareInterval(days=7),
                is_active=True,
                created_at=now,
            )

            user_plant = await uow.user_plants.save(UserPlant(
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

            sample = await uow.identification_samples.save(PlantIdentificationSample.create(
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
            await uow.users.save(user)
            await uow.commit()

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
