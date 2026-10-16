"""IDs do dataset de treino: anônimos, sem ligação de volta com o usuário."""
from typing import NewType
from uuid import UUID

TrainingIdentificationSampleId = NewType("TrainingIdentificationSampleId", UUID)
TrainingHealthSampleId = NewType("TrainingHealthSampleId", UUID)
TrainingFeedbackId = NewType("TrainingFeedbackId", UUID)
