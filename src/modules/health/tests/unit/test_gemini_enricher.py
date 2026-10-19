import json
from dataclasses import dataclass, field

import httpx
import pytest
from google.genai import errors as genai_errors

from src.modules.health.adapters.gemini.enricher import GeminiHealthEnricher
from src.shared.domain import ExternalServiceError

_REQUEST = httpx.Request("POST", "https://provider.test")


@dataclass
class _Response:
    text: str


@dataclass
class _FakeModels:
    """Faz o papel de `client.models` do SDK: devolve `outcome` (texto) ou o lança (erro)."""
    outcome: str | Exception
    calls: list[dict[str, object]] = field(default_factory=list)

    def generate_content(self, **kwargs: object) -> _Response:
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return _Response(self.outcome)


@dataclass
class _FakeSdk:
    models: _FakeModels


def _enricher(models: _FakeModels) -> GeminiHealthEnricher:
    enricher = GeminiHealthEnricher(api_key="test")
    enricher._client._client = _FakeSdk(models)
    return enricher


_DIAGNOSIS = {
    "severity": "moderate",
    "vitality_score": 0.4,
    "issues_detected": ["leaf_spots"],
    "treatment_plan": ["Remover folhas afetadas"],
    "recovery_estimate_days": 14,
    "notes": None,
}


async def test_structured_response_becomes_the_enrichment() -> None:
    # Arrange
    enricher = _enricher(_FakeModels(json.dumps(_DIAGNOSIS)))

    # Act
    result = await enricher.diagnose_health("Monstera deliciosa", ["leaf_spots"])

    # Assert
    assert (result.vitality_score, result.treatment_plan, result.recovery_estimate_days) == (0.4, ("Remover folhas afetadas",), 14)


async def test_requests_structured_output_with_the_plant_and_its_issues() -> None:
    # Arrange
    models = _FakeModels(json.dumps(_DIAGNOSIS))

    # Act
    await _enricher(models).diagnose_health("Monstera deliciosa", ["leaf_spots"])

    # Assert
    (call,) = models.calls
    config = call["config"]
    assert getattr(config, "response_mime_type") == "application/json"
    assert getattr(config, "response_schema").__name__ == "HealthDiagnosisSchema"
    assert "Monstera deliciosa" in str(call["contents"]) and "leaf_spots" in str(call["contents"])


async def test_disease_analysis_reuses_the_diagnosis() -> None:
    # Arrange
    enricher = _enricher(_FakeModels(json.dumps(_DIAGNOSIS)))

    # Act
    result = await enricher.analyze_disease("Monstera deliciosa", "leaf_spots")

    # Assert
    assert (result.disease_name, result.symptoms, result.treatment_steps) == ("leaf_spots", ("leaf_spots",), ("Remover folhas afetadas",))


@pytest.mark.parametrize(
    ("exc", "retryable"),
    [
        (genai_errors.ServerError(503, {}), True),
        (genai_errors.ClientError(429, {}), True),
        (genai_errors.ClientError(400, {}), False),
        (httpx.ConnectError("down", request=_REQUEST), True),
    ],
)
async def test_provider_errors_become_external_errors(exc: Exception, retryable: bool) -> None:
    # Arrange
    enricher = _enricher(_FakeModels(exc))

    # Act & Assert
    with pytest.raises(ExternalServiceError) as raised:
        await enricher.diagnose_health("Monstera deliciosa", ["leaf_spots"])
    assert raised.value.retryable is retryable
    assert "Gemini" in raised.value.message


@pytest.mark.parametrize("text", [
    "not json",
    json.dumps({"vitality_score": 0.4}),  # campos obrigatórios ausentes: antes virava vitalidade 1.0 em silêncio
    json.dumps({**_DIAGNOSIS, "severity": "terrible"}),
    json.dumps({**_DIAGNOSIS, "vitality_score": 7.0}),
])
async def test_response_outside_the_schema_is_a_provider_failure(text: str) -> None:
    # Arrange
    enricher = _enricher(_FakeModels(text))

    # Act & Assert
    with pytest.raises(ExternalServiceError) as raised:
        await enricher.diagnose_health("Monstera deliciosa", [])
    assert raised.value.retryable is False
