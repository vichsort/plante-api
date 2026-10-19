"""Dublês do health para os testes daqui: portas em memória, provedores com resposta fixa e fábricas."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import uuid4

from src.modules.garden import UserPlantId
from src.modules.health.domain.entities.health_record import HealthRecord
from src.modules.health.domain.ports.health_analyzer import (
    DiseaseHint,
    HealthAssessmentResult,
    IHealthAnalyzer,
)
from src.modules.health.domain.ports.health_enricher import (
    DiseaseAnalysisResult,
    HealthDiagnosisEnrichment,
    IHealthEnricher,
)
from src.modules.health.domain.ports.health_record_repository import (
    IHealthRecordRepository,
)
from src.modules.health.domain.ports.unit_of_work import IHealthUnitOfWork
from src.modules.health.domain.value_objects.ids import HealthRecordId
from src.modules.training import (
    DiseaseSuggestion,
    HealthSeverity,
    HealthSignals,
    TrainingHealthSampleId,
)
from src.shared.domain import ExternalServiceError, UserId


def make_assessment(health_probability: float = 0.1) -> HealthAssessmentResult:
    """Avaliação do Kindwise com uma doença e uma imagem de referência dela."""
    return HealthAssessmentResult(
        is_healthy=health_probability >= 0.5,
        health_probability=health_probability,
        diseases=(DiseaseHint("leaf_spots", 0.8, ("https://kindwise.test/ref.jpg",)),),
        signals=HealthSignals(
            provider="kindwise",
            is_healthy_probability=health_probability,
            diseases=(DiseaseSuggestion("leaf_spots", 0.8),),
        ),
    )


def make_health_record(
    user_id: UserId | None = None,
    user_plant_id: UserPlantId | None = None,
    training_sample_id: TrainingHealthSampleId | None = None,
    diagnosed_at: datetime | None = None,
) -> HealthRecord:
    return HealthRecord(
        id=HealthRecordId(uuid4()),
        user_plant_id=user_plant_id or UserPlantId(uuid4()),
        scientific_name="Monstera deliciosa",
        vitality_score=0.4,
        severity=HealthSeverity.MODERATE,
        source="kindwise",
        image_key="identifications/health.jpg",
        training_sample_id=training_sample_id or TrainingHealthSampleId(uuid4()),
        diagnosed_at=diagnosed_at or datetime.now(UTC),
        user_id=user_id or UserId(uuid4()),
        issues_detected=("leaf_spots",),
        treatment_plan=("Remover folhas afetadas",),
    )


@dataclass
class StubHealthAnalyzer(IHealthAnalyzer):
    """Responde sempre `result`; guarda as imagens recebidas."""
    result: HealthAssessmentResult = field(default_factory=make_assessment)
    received: list[bytes] = field(default_factory=list)

    async def assess_health(self, image_bytes: bytes) -> HealthAssessmentResult:
        self.received.append(image_bytes)
        return self.result


@dataclass
class StubHealthEnricher(IHealthEnricher):
    """Responde `enrichment` (ou lança `failure`); guarda os pedidos de diagnóstico (nome, problemas)."""
    enrichment: HealthDiagnosisEnrichment = field(
        default_factory=lambda: HealthDiagnosisEnrichment(vitality_score=0.5, treatment_plan=("water less",))
    )
    failure: ExternalServiceError | None = None
    requests: list[tuple[str, list[str]]] = field(default_factory=list)

    async def analyze_disease(self, scientific_name: str, disease_name: str) -> DiseaseAnalysisResult:
        return DiseaseAnalysisResult(scientific_name=scientific_name, disease_name=disease_name, source="gemini")

    async def diagnose_health(self, scientific_name: str, issues: list[str]) -> HealthDiagnosisEnrichment:
        self.requests.append((scientific_name, issues))
        if self.failure is not None:
            raise self.failure
        return self.enrichment


class InMemoryHealthRecordRepository(IHealthRecordRepository):
    def __init__(self, *records: HealthRecord) -> None:
        self.by_id: dict[HealthRecordId, HealthRecord] = {record.id: record for record in records}

    async def save(self, record: HealthRecord) -> HealthRecord:
        self.by_id[record.id] = record
        return record

    async def get_for_user(self, record_id: HealthRecordId, user_id: UserId) -> HealthRecord | None:
        record = self.by_id.get(record_id)
        return record if record is not None and record.user_id == user_id else None

    async def list_by_plant(self, user_plant_id: UserPlantId, limit: int = 20) -> list[HealthRecord]:
        records = [record for record in self.by_id.values() if record.user_plant_id == user_plant_id]
        records.sort(key=lambda record: record.diagnosed_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        return records[:limit]


class FakeHealthUnitOfWork(IHealthUnitOfWork):
    """Diagnósticos em memória (gravados na hora, sem rollback), transações abertas e commits."""

    def __init__(self, health_records: InMemoryHealthRecordRepository | None = None) -> None:
        self.health_records: InMemoryHealthRecordRepository = health_records or InMemoryHealthRecordRepository()
        self.opened = 0
        self.commits = 0

    @property
    def joined(self) -> bool:
        return False

    async def __aenter__(self) -> Self:
        self.opened += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1
