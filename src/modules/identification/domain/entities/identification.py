from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from src.modules.catalog import PlantSpeciesId
from src.modules.identification.domain.value_objects.ids import IdentificationId
from src.modules.training import IdentificationOrigin, TrainingIdentificationSampleId
from src.shared.domain import UserId


@dataclass(frozen=True)
class Identification:
    """
    "Identifiquei esta foto": histórico do usuário (dado pessoal, apagado com ele). Recebe o
    feedback e é a origem de uma planta no jardim.

    `training_sample_id` é o vínculo de mão única com a amostra de treino anônima: a amostra
    nunca aponta de volta, e o vínculo some quando a identificação é apagada.
    """
    id: IdentificationId
    user_id: UserId
    training_sample_id: TrainingIdentificationSampleId
    species_id: PlantSpeciesId
    scientific_name: str
    confidence: float
    source: IdentificationOrigin
    image_key: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be empty.")
        if not self.image_key:
            raise ValueError("image_key cannot be empty.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")

    @classmethod
    def create(
        cls,
        user_id: UserId,
        training_sample_id: TrainingIdentificationSampleId,
        species_id: PlantSpeciesId,
        scientific_name: str,
        confidence: float,
        source: IdentificationOrigin,
        image_key: str,
        created_at: datetime,
    ) -> "Identification":
        return cls(
            id=IdentificationId(uuid4()),
            user_id=user_id,
            training_sample_id=training_sample_id,
            species_id=species_id,
            scientific_name=scientific_name,
            confidence=confidence,
            source=source,
            image_key=image_key,
            created_at=created_at,
        )
