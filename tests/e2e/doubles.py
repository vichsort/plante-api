"""
Dublês das bordas externas (provedores de IA, S3, SES, fila do Celery). Todo o resto roda de
verdade nos testes ponta a ponta: rotas, middlewares, use cases, Unit of Work, Postgres e Redis.
"""
from dataclasses import dataclass, field

from src.domain.entities.plant_reference_image import ImageSource
from src.domain.entities.plant_species import LightRequirement
from src.domain.ports.email_sender import IEmailSender
from src.domain.ports.health_analyzer import (
    DiseaseHint,
    HealthAssessmentResult,
    IHealthAnalyzer,
)
from src.domain.ports.plant_enricher import (
    DiseaseAnalysisResult,
    EnrichmentResult,
    HealthDiagnosisEnrichment,
    IPlantEnricher,
    NutritionalEnrichmentResult,
)
from src.domain.ports.plant_identifier import (
    IdentificationResult,
    IPlantIdentifier,
    SimilarImage,
)
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.modules.training import DiseaseSuggestion, HealthSignals
from src.shared.domain import IImageStorage, UserId
from tests.factories import make_identification_signals


class FakeIdentifier(IPlantIdentifier):
    """Responde sempre a mesma espécie; guarda o que recebeu (a imagem já deve chegar limpa)."""

    def __init__(self) -> None:
        self.received: list[bytes] = []
        self.scientific_name = "Monstera deliciosa"

    async def identify(
        self,
        image_bytes: bytes,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        self.received.append(image_bytes)
        return IdentificationResult(
            scientific_name=self.scientific_name,
            confidence=ConfidenceScore(0.9),
            source="consensus",
            family="Araceae",
            genus="Monstera",
            common_names=("costela-de-adão",),
            similar_images=(SimilarImage(url="https://provider.test/ref.jpg", similarity=0.8, source=ImageSource.KINDWISE_SIMILAR),),
            signals=make_identification_signals(),
        )


class FakeHealthAnalyzer(IHealthAnalyzer):
    """Planta doente (probabilidade de saúde 0.3), com uma doença e uma imagem de referência."""

    async def assess_health(self, image_bytes: bytes) -> HealthAssessmentResult:
        return HealthAssessmentResult(
            is_healthy=False,
            health_probability=0.3,
            diseases=(DiseaseHint("leaf_spots", 0.8, ("https://provider.test/disease.jpg",)),),
            signals=HealthSignals(
                provider="kindwise",
                is_healthy_probability=0.3,
                diseases=(DiseaseSuggestion("leaf_spots", 0.8),),
            ),
        )


class FakeEnricher(IPlantEnricher):
    async def enrich_species(self, scientific_name: str) -> EnrichmentResult:
        return EnrichmentResult(
            scientific_name=scientific_name, source="gemini", light_requirement=LightRequirement.INDIRECT,
        )

    async def enrich_nutritional(self, scientific_name: str) -> NutritionalEnrichmentResult:
        return NutritionalEnrichmentResult(scientific_name=scientific_name, source="gemini")

    async def analyze_disease(self, scientific_name: str, disease_name: str) -> DiseaseAnalysisResult:
        return DiseaseAnalysisResult(scientific_name=scientific_name, disease_name=disease_name, source="gemini")

    async def diagnose_health(self, scientific_name: str, issues: list[str]) -> HealthDiagnosisEnrichment:
        return HealthDiagnosisEnrichment(
            vitality_score=0.4,
            treatment_plan=("Remover folhas manchadas",),
            recovery_estimate_days=14,
            notes="Excesso de umidade",
        )


class FakeStorage(IImageStorage):
    """Chaves previsíveis; guarda os bytes enviados para conferir que chegaram sem metadados."""

    def __init__(self) -> None:
        self.uploads: dict[str, bytes] = {}
        self.rehosted: list[str] = []

    async def upload_identification_image(
        self, image_bytes: bytes, scientific_name: str, confidence_value: float, user_id: UserId,
    ) -> str:
        key = f"identifications/{len(self.uploads)}.jpg"
        self.uploads[key] = image_bytes
        return key

    async def download_and_rehost(self, external_url: str, scientific_name: str) -> str:
        self.rehosted.append(external_url)
        return f"references/{len(self.rehosted)}.jpg"

    async def upload_training_image(self, image_bytes: bytes, scientific_name: str) -> str:
        key = f"training/{len(self.uploads)}.jpg"
        self.uploads[key] = image_bytes
        return key


@dataclass
class SentEmail:
    to: str
    code: str | None = None


class FakeEmailSender(IEmailSender):
    def __init__(self) -> None:
        self.sent: list[SentEmail] = []

    async def send_verification_code(self, to_email: str, code: str) -> None:
        self.sent.append(SentEmail(to=to_email, code=code))

    async def send_password_changed_notice(self, to_email: str) -> None:
        self.sent.append(SentEmail(to=to_email))

    def last_code_to(self, email: str) -> str:
        codes = [mail.code for mail in self.sent if mail.to == email and mail.code is not None]
        assert codes, f"no verification code was sent to {email}"
        return codes[-1]


@dataclass
class QueuedTask:
    name: str
    kwargs: dict[str, str]


@dataclass
class RecordingQueue:
    """Faz o papel do Celery para o `CeleryPublisher` real: guarda as tasks em vez de enfileirar."""
    tasks: list[QueuedTask] = field(default_factory=list)

    def send_task(self, name: str, *, kwargs: dict[str, str]) -> object:
        self.tasks.append(QueuedTask(name=name, kwargs=kwargs))
        return None
