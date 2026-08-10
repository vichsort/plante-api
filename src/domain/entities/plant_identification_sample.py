from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class SampleStatus(Enum):
    PENDING     = "pending"
    CONFIRMED   = "confirmed"
    REJECTED    = "rejected"

@dataclass(frozen=True)
class PlantIdentificationSample:
    """
    Registro imutável de uma identificação para uso futuro em treino de IA.
    Não contém dados pessoais — user_id é anonimizado após confirmação.
    """
    id: Any
    scientific_name: str
    species_id: Any
    user_image_key: str
    identification_confidence: float
    identification_source: str
    raw_response: dict
    status: SampleStatus
    created_at: datetime

    user_id: Any = None
    confirmed_at: datetime | None = None
    rejected_at: datetime | None = None

    has_deep_analysis: bool = False
    has_nutritional_analysis: bool = False

    def __post_init__(self) -> None:
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be empty.")
        if not self.user_image_key:
            raise ValueError("user_image_key cannot be empty.")
        if not 0.0 <= self.identification_confidence <= 1.0:
            raise ValueError("identification_confidence must be between 0.0 and 1.0.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")
        if self.status == SampleStatus.CONFIRMED and self.confirmed_at is None:
            raise ValueError("confirmed samples must have confirmed_at.")
        if self.status == SampleStatus.REJECTED and self.rejected_at is None:
            raise ValueError("rejected samples must have rejected_at.")

    @classmethod
    def create(
        cls,
        scientific_name: str,
        species_id: Any,
        user_image_key: str,
        identification_confidence: float,
        identification_source: str,
        raw_response: dict,
        user_id: Any,
        created_at: datetime,
    ) -> "PlantIdentificationSample":
        return cls(
            id=None,
            scientific_name=scientific_name,
            species_id=species_id,
            user_image_key=user_image_key,
            identification_confidence=identification_confidence,
            identification_source=identification_source,
            raw_response=raw_response,
            status=SampleStatus.PENDING,
            created_at=created_at,
            user_id=user_id,
        )

    def confirm(self, confirmed_at: datetime) -> "PlantIdentificationSample":
        if confirmed_at.tzinfo is None:
            raise ValueError("confirmed_at must be timezone-aware.")
        return self._replace(
            status=SampleStatus.CONFIRMED,
            confirmed_at=confirmed_at,
        )

    def reject(self, rejected_at: datetime) -> "PlantIdentificationSample":
        if rejected_at.tzinfo is None:
            raise ValueError("rejected_at must be timezone-aware.")
        return self._replace(
            status=SampleStatus.REJECTED,
            rejected_at=rejected_at,
        )

    def mark_deep_analysis_done(self) -> "PlantIdentificationSample":
        return self._replace(has_deep_analysis=True)

    def mark_nutritional_analysis_done(self) -> "PlantIdentificationSample":
        return self._replace(has_nutritional_analysis=True)

    def anonymize(self) -> "PlantIdentificationSample":
        return self._replace(user_id=None)

    @property
    def is_complete_for_training(self) -> bool:
        return (
            self.status == SampleStatus.CONFIRMED
            and self.has_deep_analysis
            and self.has_nutritional_analysis
        )

    def _replace(self, **changes) -> "PlantIdentificationSample":
        from dataclasses import replace
        return replace(self, **changes)