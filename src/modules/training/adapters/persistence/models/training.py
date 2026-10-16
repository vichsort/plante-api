"""
Tabelas do dataset de treino. Anônimas por construção: sem `user_id`, sem FK para tabelas do
usuário e sem horário exato — por isso não usam o `AuditMixin` (`created_at`/`updated_at`); o
período é só o mês. `tests/integration/test_training_tables.py` (neste módulo) confere as colunas
contra uma lista permitida.
"""
import uuid
from datetime import date

from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.training.domain.entities.feedback import (
    FeedbackOrigin,
    FeedbackVerdict,
)
from src.modules.training.domain.value_objects.provenance import HealthSeverity
from src.shared.adapters import Base, enum_values
from src.shared.domain import JsonValue


class _TrainingLocationColumns:
    period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    grid_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)


class TrainingIdentificationSampleModel(Base, _TrainingLocationColumns):
    __tablename__ = "training_identification_samples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    family: Mapped[str | None] = mapped_column(String(255), nullable=True)
    genus: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gbif_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    low_confidence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    signals: Mapped[JsonValue] = mapped_column(JSON, nullable=False)


class TrainingHealthSampleModel(Base, _TrainingLocationColumns):
    __tablename__ = "training_health_samples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    vitality_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[HealthSeverity] = mapped_column(
        SAEnum(HealthSeverity, values_callable=enum_values, name="healthSeverity"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    issues_detected: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    treatment_plan: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reference_image_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    recovery_estimate_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    signals: Mapped[JsonValue] = mapped_column(JSON, nullable=False)


class TrainingFeedbackModel(Base):
    __tablename__ = "training_feedback"
    __table_args__ = (
        CheckConstraint(
            "(identification_sample_id IS NULL) <> (health_sample_id IS NULL)",
            name="ck_training_feedback_one_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    identification_sample_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_identification_samples.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    health_sample_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_health_samples.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    verdict: Mapped[FeedbackVerdict] = mapped_column(
        SAEnum(FeedbackVerdict, values_callable=enum_values, name="feedbackVerdict"),
        nullable=False,
    )
    origin: Mapped[FeedbackOrigin] = mapped_column(
        SAEnum(FeedbackOrigin, values_callable=enum_values, name="feedbackOrigin"),
        nullable=False,
    )
    suggested_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    given_on: Mapped[date] = mapped_column(Date, nullable=False)
