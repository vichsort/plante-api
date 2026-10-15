from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from src.domain.entities.health_record import HealthRecord, HealthSeverity
from src.domain.exceptions import (
    ExternalServiceError,
    PlantNotFoundError,
    UserNotFoundError,
)
from src.domain.policies.subscription_policy import SubscriptionPolicy
from src.domain.ports.health_analyzer import IHealthAnalyzer
from src.domain.ports.health_raw_response_repository import IHealthRawResponseRepository
from src.domain.ports.health_record_repository import IHealthRecordRepository
from src.domain.ports.image_storage import IImageStorage
from src.domain.ports.plant_enricher import IPlantEnricher
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.ports.user_repository import IUserRepository

log = structlog.get_logger()


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
    user_id: Any
    user_plant_id: Any
    image_bytes: bytes

class DiagnoseHealthUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        user_plant_repo: IUserPlantRepository,
        health_repo: IHealthRecordRepository,
        health_analyzer: IHealthAnalyzer,
        plant_enricher: IPlantEnricher,
        storage: IImageStorage,
        health_raw_repo: IHealthRawResponseRepository,
    ) -> None:
        self._user_repo = user_repo
        self._user_plant_repo = user_plant_repo
        self._health_repo = health_repo
        self._health_analyzer = health_analyzer
        self._plant_enricher = plant_enricher
        self._storage = storage
        self._health_raw_repo = health_raw_repo

    async def execute(self, dto: DiagnoseHealthInputDTO) -> dict[str, Any]:
        now = datetime.now(UTC)

        user = await self._user_repo.get_by_id(dto.user_id)
        if not user:
            raise UserNotFoundError(user_id=dto.user_id)

        user_plant = await self._user_plant_repo.get_by_id(dto.user_plant_id, dto.user_id)
        if not user_plant:
            raise PlantNotFoundError(dto.user_plant_id)

        user.consume_identify_token()

        assessment = await self._health_analyzer.assess_health(dto.image_bytes)

        issues = [d.name for d in assessment.diseases]
        gemini_data: dict[str, Any] = {}

        if assessment.health_probability < SubscriptionPolicy.health_unhealthy_threshold():
            # Gemini é complementar: se falhar, o diagnóstico segue só com o Kindwise
            try:
                gemini_data = await self._plant_enricher.diagnose_health(
                    scientific_name=user_plant.scientific_name,
                    issues=issues,
                )
            except ExternalServiceError as exc:
                log.warning("diagnose.enrichment_unavailable", error=exc.message)
            else:
                # Token extra só é cobrado quando a análise complementar foi entregue
                user.consume_identify_token()

        vitality = gemini_data.get("vitality_score", assessment.health_probability)
        severity = _map_severity(vitality)

        image_key = await self._storage.upload_identification_image(
            image_bytes=dto.image_bytes,
            scientific_name=user_plant.scientific_name,
            confidence_value=vitality,
            user_id=dto.user_id,
        )

        record = await self._health_repo.save(HealthRecord(
            id=None,
            user_plant_id=dto.user_plant_id,
            user_id=dto.user_id,
            scientific_name=user_plant.scientific_name,
            diagnosed_at=now,
            vitality_score=vitality,
            severity=severity,
            source="kindwise" if not gemini_data else "kindwise+gemini",
            image_key=image_key,
            issues_detected=tuple(issues),
            treatment_plan=tuple(gemini_data.get("treatment_plan", [])),
            recovery_estimate_days=gemini_data.get("recovery_estimate_days"),
            notes=gemini_data.get("notes"),
        ))

        await self._user_repo.save(user)

        await self._health_raw_repo.save(record.id, assessment.raw_response)

        return {
            "health_record_id": record.id,
            "severity": record.severity.value,
            "vitality_score": record.vitality_score,
            "is_healthy": record.is_healthy,
            "issues_detected": list(record.issues_detected),
            "treatment_plan": list(record.treatment_plan),
            "recovery_estimate_days": record.recovery_estimate_days,
            "image_key": record.image_key,
            "similar_images_urls": list(assessment.all_similar_images_urls),
        }