from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import structlog

from src.domain.entities.health_record import HealthRecord, HealthSeverity
from src.domain.exceptions import (
    ExternalServiceError,
    InvalidImageError,
    PlantNotFoundError,
    UserNotFoundError,
)
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.health_analyzer import IHealthAnalyzer
from src.domain.ports.health_raw_response_repository import (
    IHealthRawResponseRepository,
    PendingHealthAssessment,
)
from src.domain.ports.image_storage import IImageStorage
from src.domain.ports.plant_enricher import HealthDiagnosisEnrichment, IPlantEnricher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import HealthRecordId, UserId, UserPlantId

log = structlog.stdlib.get_logger()


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

@dataclass(frozen=True)
class DiagnoseHealthOutput:
    record: HealthRecord
    similar_images_urls: tuple[str, ...]


class DiagnoseHealthUseCase:
    raises = (ExternalServiceError, InvalidImageError, PlantNotFoundError, UserNotFoundError)

    def __init__(
        self,
        uow: IUnitOfWork,
        health_analyzer: IHealthAnalyzer,
        plant_enricher: IPlantEnricher,
        storage: IImageStorage,
        health_raw_repo: IHealthRawResponseRepository,
    ) -> None:
        self._uow = uow
        self._health_analyzer = health_analyzer
        self._plant_enricher = plant_enricher
        self._storage = storage
        self._health_raw_repo = health_raw_repo

    async def execute(self, dto: DiagnoseHealthInputDTO) -> DiagnoseHealthOutput:
        now = datetime.now(UTC)

        # 1. Leitura curta: a transação não fica aberta durante as chamadas à IA e ao S3
        async with self._uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if not user:
                raise UserNotFoundError(user_id=dto.user_id)

            user_plant = await uow.user_plants.get_by_id(dto.user_plant_id, dto.user_id)
            if not user_plant:
                raise PlantNotFoundError(dto.user_plant_id)

        # 2. Serviços externos
        assessment = await self._health_analyzer.assess_health(dto.image_bytes)

        issues = [d.name for d in assessment.diseases]
        enrichment: HealthDiagnosisEnrichment | None = None
        if assessment.health_probability < SubscriptionPolicy.health_unhealthy_threshold():
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

        image_key = await self._storage.upload_identification_image(
            image_bytes=dto.image_bytes,
            scientific_name=user_plant.scientific_name,
            confidence_value=vitality,
            user_id=dto.user_id,
        )

        # 3. Escrita; o usuário é relido para cobrar os tokens sobre o estado atual
        async with self._uow as uow:
            user = await uow.users.get_by_id(dto.user_id)
            if not user:
                raise UserNotFoundError(user_id=dto.user_id)

            user.consume_identify_token()
            if enrichment:
                # Token extra só é cobrado quando a análise complementar foi entregue
                user.consume_identify_token()

            record = await uow.health_records.save(HealthRecord(
                id=HealthRecordId(uuid4()),
                user_plant_id=dto.user_plant_id,
                user_id=dto.user_id,
                scientific_name=user_plant.scientific_name,
                diagnosed_at=now,
                vitality_score=vitality,
                severity=severity,
                source="kindwise+gemini" if enrichment else "kindwise",
                image_key=image_key,
                issues_detected=tuple(issues),
                treatment_plan=enrichment.treatment_plan if enrichment else (),
                recovery_estimate_days=enrichment.recovery_estimate_days if enrichment else None,
                notes=enrichment.notes if enrichment else None,
            ))

            await uow.users.save(user)
            await uow.commit()

        await self._health_raw_repo.save(record.id, PendingHealthAssessment(
            raw_response=assessment.raw_response,
            similar_images_urls=assessment.all_similar_images_urls,
        ))

        return DiagnoseHealthOutput(
            record=record,
            similar_images_urls=assessment.all_similar_images_urls,
        )
