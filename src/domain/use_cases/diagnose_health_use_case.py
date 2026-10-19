from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import structlog

from src.domain.entities.health_record import HealthRecord
from src.domain.ports.health_analyzer import IHealthAnalyzer
from src.domain.ports.health_enricher import HealthDiagnosisEnrichment, IHealthEnricher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import HealthRecordId
from src.modules.garden import IPlantLookup, PlantNotFoundError, UserPlantId
from src.modules.identity import IUserDirectory
from src.modules.subscription import (
    FeatureCost,
    ITokenWallet,
    SubscriptionRequiredError,
)
from src.modules.training import (
    HealthSeverity,
    HealthSource,
    ITrainingRecorder,
    TrainingHealthSample,
    TrainingLocation,
    month_of,
)
from src.shared.domain import (
    ExternalServiceError,
    IImageSanitizer,
    IImageStorage,
    InvalidImageError,
    UserId,
    UserNotFoundError,
)

log = structlog.stdlib.get_logger()

# Abaixo desta probabilidade de saúde o Gemini complementa o diagnóstico (se couber no saldo)
_UNHEALTHY_THRESHOLD = 0.5


def _map_severity(vitality: float) -> HealthSeverity:
    if vitality >= 0.85:
        return HealthSeverity.HEALTHY
    if vitality >= 0.65:
        return HealthSeverity.LOW
    if vitality >= 0.45:
        return HealthSeverity.MODERATE
    if vitality >= 0.25:
        return HealthSeverity.HIGH
    return HealthSeverity.CRITICAL

@dataclass(frozen=True)
class DiagnoseHealthInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId
    image_bytes: bytes
    latitude: float | None = None
    longitude: float | None = None

@dataclass(frozen=True)
class DiagnoseHealthOutput:
    record: HealthRecord
    similar_images_urls: tuple[str, ...]


class DiagnoseHealthUseCase:
    """
    Diagnostica a foto e grava, sem ligação de volta entre eles, o **diagnóstico** (histórico do
    usuário) e a **amostra de treino de saúde** (anônima: cópia própria da foto, sinais do
    Kindwise, mês e localização aproximada). O feedback do usuário chega depois, a qualquer
    momento (`GiveHealthFeedbackUseCase`).
    """

    raises = (ExternalServiceError, InvalidImageError, PlantNotFoundError, SubscriptionRequiredError, UserNotFoundError)

    def __init__(
        self,
        uow: IUnitOfWork,
        sanitizer: IImageSanitizer,
        health_analyzer: IHealthAnalyzer,
        plant_enricher: IHealthEnricher,
        storage: IImageStorage,
        users: IUserDirectory,
        wallet: ITokenWallet,
        training: ITrainingRecorder,
        plants: IPlantLookup,
    ) -> None:
        self._plants = plants
        self._training = training
        self._users = users
        self._wallet = wallet
        self._uow = uow
        self._sanitizer = sanitizer
        self._health_analyzer = health_analyzer
        self._plant_enricher = plant_enricher
        self._storage = storage

    async def execute(self, dto: DiagnoseHealthInputDTO) -> DiagnoseHealthOutput:
        now = datetime.now(UTC)

        # 1. Leitura curta: a transação não fica aberta durante as chamadas à IA e ao S3
        async with self._uow as uow:
            region = await self._users.region_of(dto.user_id)

            user_plant = await self._plants.get_for_user(dto.user_plant_id, dto.user_id)

            await self._wallet.ensure_can_diagnose(dto.user_id, now)
            can_enrich = await self._wallet.can_enrich_diagnosis(dto.user_id, now)

        # 2. Serviços externos, só com a foto já sem metadados (GPS, aparelho, data)
        image_bytes = self._sanitizer.sanitize(dto.image_bytes)
        assessment = await self._health_analyzer.assess_health(image_bytes)

        issues = [d.name for d in assessment.diseases]
        enrichment: HealthDiagnosisEnrichment | None = None
        if can_enrich and assessment.health_probability < _UNHEALTHY_THRESHOLD:
            # Gemini é complementar: se falhar, o diagnóstico segue só com o Kindwise
            try:
                enrichment = await self._plant_enricher.diagnose_health(
                    scientific_name=user_plant.scientific_name,
                    issues=issues,
                )
            except ExternalServiceError as exc:
                log.warning("diagnose.enrichment_unavailable", error=exc.message)

        vitality = enrichment.vitality_score if enrichment else assessment.health_probability
        severity = _map_severity(vitality)
        source: HealthSource = "kindwise+gemini" if enrichment else "kindwise"
        treatment_plan = enrichment.treatment_plan if enrichment else ()
        recovery_estimate_days = enrichment.recovery_estimate_days if enrichment else None
        notes = enrichment.notes if enrichment else None

        image_key = await self._storage.upload_identification_image(
            image_bytes=image_bytes,
            scientific_name=user_plant.scientific_name,
            confidence_value=vitality,
            user_id=dto.user_id,
        )
        training_image_key = await self._storage.upload_training_image(
            image_bytes=image_bytes,
            scientific_name=user_plant.scientific_name,
        )
        # Imagens de referência das doenças (do Kindwise, não do usuário) ficam com a amostra
        reference_keys = tuple([
            await self._storage.download_and_rehost(
                external_url=url,
                scientific_name=user_plant.scientific_name,
            )
            for url in assessment.all_similar_images_urls
        ])

        # 3. Escrita (os tokens são cobrados sobre o saldo travado nela)
        async with self._uow as uow:
            await self._wallet.charge(dto.user_id, FeatureCost.DIAGNOSIS, now)
            if enrichment:
                # Token extra só é cobrado quando a análise complementar foi entregue
                await self._wallet.charge(dto.user_id, FeatureCost.DIAGNOSIS_ENRICHMENT, now)

            training_sample = TrainingHealthSample(
                id=TrainingHealthSample.new_id(),
                image_key=training_image_key,
                scientific_name=user_plant.scientific_name,
                vitality_score=vitality,
                severity=severity,
                source=source,
                signals=assessment.signals,
                period=month_of(now),
                location=TrainingLocation.coarse(region.country, region.state, dto.latitude, dto.longitude),
                issues_detected=tuple(issues),
                treatment_plan=treatment_plan,
                reference_image_keys=reference_keys,
                recovery_estimate_days=recovery_estimate_days,
                notes=notes,
            )
            await self._training.record_health_sample(training_sample)

            record = await uow.health_records.save(HealthRecord(
                id=HealthRecordId(uuid4()),
                user_plant_id=dto.user_plant_id,
                user_id=dto.user_id,
                scientific_name=user_plant.scientific_name,
                diagnosed_at=now,
                vitality_score=vitality,
                severity=severity,
                source=source,
                image_key=image_key,
                training_sample_id=training_sample.id,
                issues_detected=tuple(issues),
                treatment_plan=treatment_plan,
                recovery_estimate_days=recovery_estimate_days,
                notes=notes,
            ))

            await uow.commit()

        return DiagnoseHealthOutput(
            record=record,
            similar_images_urls=assessment.all_similar_images_urls,
        )
