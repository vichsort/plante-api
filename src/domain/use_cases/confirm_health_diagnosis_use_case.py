from dataclasses import dataclass
from datetime import datetime, timezone

from src.domain.entities.health_identification_sample import (
    HealthIdentificationSample,
    HealthSampleStatus,
)
from src.domain.events.domain_events import HealthDiagnosisConfirmedEvent
from src.domain.exceptions import HealthRecordNotFoundError, UserNotFoundError
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.health_identification_sample_repository import (
    IHealthIdentificationSampleRepository,
)
from src.domain.ports.health_record_repository import IHealthRecordRepository
from src.domain.ports.image_storage import IImageStorage
from src.domain.ports.user_repository import IUserRepository

@dataclass(frozen=True)
class ConfirmHealthDiagnosisInputDTO:
    user_id: int
    health_record_id: int
    reference_image_url: str    # URL da imagem similar do Kindwise escolhida pelo frontend
    raw_response: dict          # JSON bruto do Kindwise, enviado pelo frontend após o diagnóstico


class ConfirmHealthDiagnosisUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        health_record_repo: IHealthRecordRepository,
        health_sample_repo: IHealthIdentificationSampleRepository,
        storage: IImageStorage,
        publisher: IDomainPublisher,
    ) -> None:
        self._user_repo = user_repo
        self._health_record_repo = health_record_repo
        self._health_sample_repo = health_sample_repo
        self._storage = storage
        self._publisher = publisher

    async def execute(self, dto: ConfirmHealthDiagnosisInputDTO) -> dict:
        now = datetime.now(timezone.utc)

        user = await self._user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(dto.user_id)

        record = await self._health_record_repo.get_by_id(dto.health_record_id)
        if record is None:
            raise HealthRecordNotFoundError(dto.health_record_id)

        # Re-hospeda a imagem similar do Kindwise no S3
        reference_key = await self._storage.download_and_rehost(
            external_url=dto.reference_image_url,
            scientific_name=record.scientific_name,
        )

        sample = HealthIdentificationSample(
            id=None,
            health_record_id=record.id,
            scientific_name=record.scientific_name,
            user_image_key=record.image_key,
            reference_image_key=reference_key,
            vitality_score=record.vitality_score,
            issues_detected=record.issues_detected,
            treatment_plan=record.treatment_plan,
            identification_source=record.source,
            raw_response=dto.raw_response,
            status=HealthSampleStatus.CONFIRMED,
            created_at=now,
            user_id=dto.user_id,
            confirmed_at=now,
            recovery_estimate_days=record.recovery_estimate_days,
            notes=record.notes,
        )

        saved = await self._health_sample_repo.save(sample)

        await self._publisher.publish(
            HealthDiagnosisConfirmedEvent.create(
                user_id=dto.user_id,
                health_record_id=record.id,
                sample_id=saved.id,
                scientific_name=record.scientific_name,
            )
        )

        return {
            "sample_id": saved.id,
            "health_record_id": record.id,
            "scientific_name": record.scientific_name,
            "status": saved.status.value,
            "confirmed_at": saved.confirmed_at.isoformat(),
        }