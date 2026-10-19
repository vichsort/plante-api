from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.catalog import ISpeciesRegistry
from src.modules.identification.domain.entities.identification import Identification
from src.modules.identification.domain.events import PlantIdentifiedEvent
from src.modules.identification.domain.exceptions import (
    LowConfidenceError,
    NotAPlantError,
)
from src.modules.identification.domain.ports.plant_identifier import IPlantIdentifier
from src.modules.identification.domain.ports.unit_of_work import (
    IIdentificationUnitOfWork,
)
from src.modules.identification.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from src.modules.identification.domain.value_objects.ids import IdentificationId
from src.modules.identity import IUserDirectory
from src.modules.quota import (
    DailyQuotaExceededError,
    FeatureCost,
    ITokenWallet,
)
from src.modules.training import (
    ITrainingRecorder,
    TrainingIdentificationSample,
    TrainingLocation,
    month_of,
)
from src.shared.domain import (
    ExternalServiceError,
    IDomainPublisher,
    IImageSanitizer,
    IImageStorage,
    InvalidImageError,
    UserId,
    UserNotFoundError,
)


@dataclass(frozen=True)
class IdentifyPlantInputDTO:
    user_id: UserId
    image_bytes: bytes
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class IdentifyPlantOutput:
    identification_id: IdentificationId
    scientific_name: str
    confidence: ConfidenceScore
    image_url: str
    needs_human_review: bool


class IdentifyPlantUseCase:
    """
    Identifica a foto e grava duas coisas sem ligação de volta entre elas:
    - a **identificação** (histórico do usuário, dado pessoal), que guarda o vínculo de mão única
      para a amostra de treino;
    - a **amostra de treino** (anônima): cópia própria da foto, rótulo, sinais dos provedores,
      mês e localização aproximada.
    Não cria planta no jardim: isso é uma ação separada (`AddPlantToGardenUseCase`).
    """

    raises = (
        ExternalServiceError,
        InvalidImageError,
        LowConfidenceError,
        NotAPlantError,
        DailyQuotaExceededError,
        UserNotFoundError,
    )

    def __init__(
        self,
        uow: IIdentificationUnitOfWork,
        sanitizer: IImageSanitizer,
        plant_identifier: IPlantIdentifier,
        storage: IImageStorage,
        publisher: IDomainPublisher,
        users: IUserDirectory,
        wallet: ITokenWallet,
        training: ITrainingRecorder,
        catalog: ISpeciesRegistry,
    ) -> None:
        self.training = training
        self.catalog = catalog
        self.uow = uow
        self.sanitizer = sanitizer
        self.plant_identifier = plant_identifier
        self.storage = storage
        self.publisher = publisher
        self.users = users
        self.wallet = wallet

    async def execute(self, dto: IdentifyPlantInputDTO) -> IdentifyPlantOutput:
        now = datetime.now(UTC)

        # 1. Leituras curtas: nenhuma transação fica aberta durante as chamadas à IA e ao S3
        region = await self.users.region_of(dto.user_id)
        await self.wallet.ensure_can_identify(dto.user_id, now)

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
        training_image_key = await self.storage.upload_training_image(
            image_bytes=image_bytes,
            scientific_name=result.scientific_name,
        )

        rehosted = [
            (await self.storage.download_and_rehost(
                external_url=similar.url,
                scientific_name=result.scientific_name,
            ), similar.source)
            for similar in result.similar_images
        ]

        # 3. Escrita numa transação só (o token é cobrado sobre o saldo travado nela)
        async with self.uow as uow:
            await self.catalog.add_reference_images(result.scientific_name, rehosted, at=now)
            species = await self.catalog.register_identified(
                scientific_name=result.scientific_name,
                family=result.family,
                genus=result.genus,
                common_names=result.common_names,
                provider_entity_id=result.provider_entity_id,
                gbif_id=result.gbif_id,
            )

            training_sample = TrainingIdentificationSample(
                id=TrainingIdentificationSample.new_id(),
                image_key=training_image_key,
                scientific_name=result.scientific_name,
                confidence=result.confidence.value,
                source=result.source,
                low_confidence=result.low_confidence,
                signals=result.signals,
                period=month_of(now),
                location=TrainingLocation.coarse(region.country, region.state, dto.latitude, dto.longitude),
                family=result.family,
                genus=result.genus,
                gbif_id=result.gbif_id,
                provider_entity_id=result.provider_entity_id,
            )
            await self.training.record_identification_sample(training_sample)

            identification = await uow.identifications.save(Identification.create(
                user_id=dto.user_id,
                training_sample_id=training_sample.id,
                species_id=species.id,
                scientific_name=result.scientific_name,
                confidence=result.confidence.value,
                source=result.source,
                image_key=user_image_key,
                created_at=now,
            ))

            await self.wallet.charge(dto.user_id, FeatureCost.IDENTIFY, now)
            await uow.commit()

        await self.publisher.publish(PlantIdentifiedEvent.create(
            user_id=dto.user_id,
            species_id=species.id,
            is_first_plant=False,
        ))

        return IdentifyPlantOutput(
            identification_id=identification.id,
            scientific_name=species.scientific_name,
            confidence=result.confidence,
            image_url=user_image_key,
            needs_human_review=result.confidence.requires_human_review(),
        )
