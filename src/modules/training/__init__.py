"""
training: o dataset anônimo que treina a IA própria do PlantE (README.md). A API pública é só
domínio; a composição monta o módulo por `src.modules.training.container`.
"""
from src.modules.training.domain.entities.feedback import (
    FeedbackOrigin,
    FeedbackTarget,
    FeedbackVerdict,
    HealthLabel,
    IdentificationLabel,
    TrainingFeedback,
)
from src.modules.training.domain.entities.samples import (
    TrainingHealthSample,
    TrainingIdentificationSample,
)
from src.modules.training.domain.services.recorder import ITrainingRecorder
from src.modules.training.domain.value_objects.ids import (
    TrainingFeedbackId,
    TrainingHealthSampleId,
    TrainingIdentificationSampleId,
)
from src.modules.training.domain.value_objects.location import (
    TrainingLocation,
    month_of,
)
from src.modules.training.domain.value_objects.provenance import (
    HealthSeverity,
    HealthSource,
    IdentificationOrigin,
    IdentificationProvider,
    parse_health_source,
    parse_identification_origin,
)
from src.modules.training.domain.value_objects.provider_signals import (
    DiseaseSuggestion,
    HealthSignals,
    IdentificationSignals,
    SpeciesSuggestion,
)

__all__ = [
    "DiseaseSuggestion",
    "FeedbackOrigin",
    "FeedbackTarget",
    "FeedbackVerdict",
    "HealthLabel",
    "HealthSeverity",
    "HealthSignals",
    "HealthSource",
    "ITrainingRecorder",
    "IdentificationLabel",
    "IdentificationOrigin",
    "IdentificationProvider",
    "IdentificationSignals",
    "SpeciesSuggestion",
    "TrainingFeedback",
    "TrainingFeedbackId",
    "TrainingHealthSample",
    "TrainingHealthSampleId",
    "TrainingIdentificationSample",
    "TrainingIdentificationSampleId",
    "TrainingLocation",
    "month_of",
    "parse_health_source",
    "parse_identification_origin",
]
