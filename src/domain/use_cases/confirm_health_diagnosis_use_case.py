from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from src.domain.entities.health_identification_sample import (
    HealthIdentificationSample,
    HealthSampleStatus,
)
from src.domain.events.domain_events import HealthDiagnosisConfirmedEvent
from src.domain.exceptions import (
    HealthRecordNotFoundError,
    RawResponseExpiredError,
    UserNotFoundError,
)
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.health_identification_sample_repository import (
    IHealthIdentificationSampleRepository,
)
from src.domain.ports.health_raw_response_repository import IHealthRawResponseRepository
from src.domain.ports.health_record_repository import IHealthRecordRepository
from src.domain.ports.image_storage import IImageStorage
from src.domain.ports.user_repository import IUserRepository
from src.domain.value_objects.ids import HealthRecordId, HealthSampleId, UserId


@dataclass(frozen=True)
class ConfirmHealthDiagnosisInputDTO:
    user_id: UserId
    health_record_id: HealthRecordId


class ConfirmHealthDiagnosisUseCase:
    raises = (HealthRecordNotFoundError, RawResponseExpiredError, UserNotFoundError)

    def __init__(
        self,
        user_repo: IUserRepository,
        health_record_repo: IHealthRecordRepository,
        health_sample_repo: IHealthIdentificationSampleRepository,
        health_raw_repo: IHealthRawResponseRepository,
        storage: IImageStorage,
        publisher: IDomainPublisher,
    ) -> None:
        self._user_repo = user_repo
        self._health_record_repo = health_record_repo
        self._health_sample_repo = health_sample_repo
        self._health_raw_repo = health_raw_repo
        self._storage = storage
        self._publisher = publisher

    async def execute(self, dto: ConfirmHealthDiagnosisInputDTO) -> HealthIdentificationSample:
        now = datetime.now(UTC)

        user = await self._user_repo.get_by_id(dto.user_id)
        if user is None:
            raise UserNotFoundError(user_id=dto.user_id)

        record = await self._health_record_repo.get_by_id(dto.health_record_id)
        if record is None or record.user_id != dto.user_id:
            raise HealthRecordNotFoundError(dto.health_record_id)

        pending = await self._health_raw_repo.get(dto.health_record_id)
        if pending is None:
            raise RawResponseExpiredError(dto.health_record_id)

        reference_keys = [
            await self._storage.download_and_rehost(
                external_url=url,
                scientific_name=record.scientific_name,
            )
            for url in pending.similar_images_urls
        ]

        sample = HealthIdentificationSample(
            id=HealthSampleId(uuid4()),
            health_record_id=record.id,
            scientific_name=record.scientific_name,
            user_image_key=record.image_key,
            reference_image_keys=tuple(reference_keys),
            vitality_score=record.vitality_score,
            issues_detected=record.issues_detected,
            treatment_plan=record.treatment_plan,
            identification_source=record.source,
            raw_response=pending.raw_response,
            status=HealthSampleStatus.CONFIRMED,
            created_at=now,
            user_id=dto.user_id,
            confirmed_at=now,
            recovery_estimate_days=record.recovery_estimate_days,
            notes=record.notes,
        )

        saved = await self._health_sample_repo.save(sample)

        await self._health_raw_repo.delete(dto.health_record_id)

        await self._publisher.publish(
            HealthDiagnosisConfirmedEvent.create(
                user_id=dto.user_id,
                health_record_id=record.id,
                sample_id=saved.id,
                scientific_name=record.scientific_name,
            )
        )

        return saved