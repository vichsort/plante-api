from datetime import date
from uuid import uuid4

import pytest

from src.modules.training.domain.entities.feedback import (
    FeedbackOrigin,
    FeedbackVerdict,
    HealthLabel,
    IdentificationLabel,
    TrainingFeedback,
)
from src.modules.training.domain.value_objects.ids import (
    TrainingHealthSampleId,
    TrainingIdentificationSampleId,
)

TODAY = date(2026, 10, 16)


def test_identification_label_keeps_a_trimmed_suggestion() -> None:
    # Arrange
    target = IdentificationLabel(TrainingIdentificationSampleId(uuid4()), "  Monstera adansonii ")

    # Act
    feedback = TrainingFeedback.create(target, FeedbackVerdict.WRONG, FeedbackOrigin.EXPLICIT, TODAY)

    # Assert
    assert feedback.target == IdentificationLabel(target.sample_id, "Monstera adansonii")


def test_blank_suggestion_is_rejected() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="blank"):
        IdentificationLabel(TrainingIdentificationSampleId(uuid4()), "   ")


def test_health_label_has_no_suggestion_at_all() -> None:
    # Arrange: antes a entidade aceitava `suggested_name` com alvo de saúde; agora o tipo não tem o campo
    target = HealthLabel(TrainingHealthSampleId(uuid4()))

    # Act
    feedback = TrainingFeedback.create(target, FeedbackVerdict.CORRECT, FeedbackOrigin.EXPLICIT, TODAY)

    # Assert
    assert not hasattr(feedback.target, "suggested_name")
