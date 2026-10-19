import json

import httpx
import pytest
from google.genai import errors as genai_errors
from structlog.testing import capture_logs

from src.adapters.ai.gemini.gemini_adapter import GeminiHealthEnricher
from src.adapters.ai.kindwise.kindwise_adapter import KindwiseHealthAnalyzer
from src.shared.adapters import KindwiseClient, translate_provider_errors
from src.shared.adapters.providers import kindwise_client
from src.shared.domain import ExternalServiceError, InvalidImageError

_REQUEST = httpx.Request("POST", "https://provider.test")
_RealAsyncClient = httpx.AsyncClient


def _status_error(status: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(
        "error", request=_REQUEST, response=httpx.Response(status, request=_REQUEST)
    )


async def _translate(exc: Exception) -> Exception:
    with pytest.raises(Exception) as raised:
        async with translate_provider_errors("Kindwise"):
            raise exc
    return raised.value


@pytest.mark.asyncio
async def test_bad_request_becomes_invalid_image():
    error = await _translate(_status_error(400))
    assert isinstance(error, InvalidImageError)
    assert error.code == "PLANTE_4013_INVALID_IMAGE"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc",
    [
        _status_error(500),
        _status_error(503),
        _status_error(429),
        httpx.ConnectError("down", request=_REQUEST),
        httpx.ReadTimeout("slow", request=_REQUEST),
    ],
)
async def test_infrastructure_failures_are_retryable(exc):
    error = await _translate(exc)
    assert isinstance(error, ExternalServiceError)
    assert error.retryable is True
    assert "Kindwise" in error.message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc", [_status_error(401), _status_error(404), httpx.TooManyRedirects("loop", request=_REQUEST)]
)
async def test_other_http_errors_are_not_retryable(exc):
    error = await _translate(exc)
    assert isinstance(error, ExternalServiceError)
    assert error.retryable is False


@pytest.mark.asyncio
async def test_non_http_errors_pass_through():
    error = await _translate(ValueError("no suggestions"))
    assert isinstance(error, ValueError)


def _patch_transport(monkeypatch, module, status: int, **response_kwargs) -> None:
    response_kwargs = response_kwargs or {"json": {}}
    transport = httpx.MockTransport(lambda request: httpx.Response(status, **response_kwargs))
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda: _RealAsyncClient(transport=transport))


def _health() -> KindwiseHealthAnalyzer:
    return KindwiseHealthAnalyzer(KindwiseClient(api_key="test"))


@pytest.mark.asyncio
async def test_kindwise_health_translates_provider_errors(monkeypatch):
    _patch_transport(monkeypatch, kindwise_client, 400, text="Invalid image data")
    with pytest.raises(InvalidImageError):
        await _health().assess_health(b"img")

    _patch_transport(monkeypatch, kindwise_client, 503)
    with pytest.raises(ExternalServiceError) as raised:
        await _health().assess_health(b"img")
    assert raised.value.retryable is True


@pytest.mark.asyncio
async def test_kindwise_health_malformed_request_is_not_invalid_image(monkeypatch):
    # Kindwise também responde 400 para payload nosso malformado
    _patch_transport(monkeypatch, kindwise_client, 400, text="Images have to be list of base64 strings")
    with capture_logs() as logs, pytest.raises(ExternalServiceError) as raised:
        await _health().assess_health(b"img")
    assert raised.value.retryable is False
    assert any(e["event"] == "provider.request_rejected" and e["log_level"] == "error" for e in logs)


def _kindwise_body(is_plant: dict | None) -> dict:
    # Formato observado na API real (gato: probability 0.09, binary false)
    result: dict = {
        "disease": {"suggestions": []},
        "is_healthy": {"binary": False, "probability": 0.05, "threshold": 0.5},
    }
    if is_plant is not None:
        result["is_plant"] = is_plant
    return {"status": "COMPLETED", "result": result}


@pytest.mark.asyncio
async def test_kindwise_health_non_plant_is_invalid_image(monkeypatch):
    body = _kindwise_body({"probability": 0.09, "threshold": 0.5, "binary": False})
    _patch_transport(monkeypatch, kindwise_client, 201, json=body)
    with pytest.raises(InvalidImageError):
        await _health().assess_health(b"img")


@pytest.mark.asyncio
@pytest.mark.parametrize("is_plant", [{"probability": 0.82, "threshold": 0.5, "binary": True}, None])
async def test_kindwise_health_plant_or_missing_is_plant_is_parsed(monkeypatch, is_plant):
    _patch_transport(monkeypatch, kindwise_client, 201, json=_kindwise_body(is_plant))
    assert (await _health().assess_health(b"img")).is_healthy is False


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_auth_errors_are_logged_as_misconfiguration(status):
    with capture_logs() as logs:
        error = await _translate(_status_error(status))
    assert isinstance(error, ExternalServiceError)
    assert error.retryable is False
    assert {"event": "provider.misconfigured", "log_level": "error", "service": "Kindwise", "status": status} in logs


@pytest.mark.asyncio
async def test_custom_invalid_image_statuses():
    with pytest.raises(InvalidImageError):
        async with translate_provider_errors("PlantNet", frozenset({404})):
            raise _status_error(404)


class _FakeModels:
    def __init__(self, outcome) -> None:
        self._outcome = outcome
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return type("Response", (), {"text": self._outcome})()


def _gemini(outcome) -> GeminiHealthEnricher:
    adapter = GeminiHealthEnricher(api_key="test")
    adapter._client._client = type("Client", (), {"models": _FakeModels(outcome)})()
    return adapter


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc, retryable",
    [
        (genai_errors.ServerError(503, {}), True),
        (genai_errors.ClientError(429, {}), True),
        (genai_errors.ClientError(400, {}), False),
        (httpx.ConnectError("down", request=_REQUEST), True),
    ],
)
async def test_gemini_translates_provider_errors(exc, retryable):
    with pytest.raises(ExternalServiceError) as raised:
        await _gemini(exc).diagnose_health("Monstera deliciosa", ["leaf_spots"])
    assert raised.value.retryable is retryable
    assert "Gemini" in raised.value.message


@pytest.mark.asyncio
async def test_gemini_invalid_json_is_external_error():
    with pytest.raises(ExternalServiceError) as raised:
        await _gemini("not json").diagnose_health("Monstera deliciosa", [])
    assert raised.value.retryable is False


_DIAGNOSIS = {
    "severity": "moderate",
    "vitality_score": 0.4,
    "issues_detected": ["leaf_spots"],
    "treatment_plan": ["Remover folhas afetadas"],
    "recovery_estimate_days": 14,
    "notes": None,
}


@pytest.mark.asyncio
async def test_gemini_structured_response_is_parsed():
    result = await _gemini(json.dumps(_DIAGNOSIS)).diagnose_health("Monstera deliciosa", ["leaf_spots"])
    assert result.vitality_score == 0.4
    assert result.treatment_plan == ("Remover folhas afetadas",)
    assert result.recovery_estimate_days == 14


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"vitality_score": 0.4},  # campos obrigatórios ausentes: antes virava vitalidade 1.0 em silêncio
    {**_DIAGNOSIS, "severity": "terrible"},
    {**_DIAGNOSIS, "vitality_score": 7.0},
])
async def test_gemini_response_outside_schema_is_external_error(payload):
    with pytest.raises(ExternalServiceError) as raised:
        await _gemini(json.dumps(payload)).diagnose_health("Monstera deliciosa", [])
    assert raised.value.retryable is False


@pytest.mark.asyncio
async def test_gemini_requests_structured_output():
    models = _FakeModels(json.dumps(_DIAGNOSIS))
    adapter = GeminiHealthEnricher(api_key="test")
    adapter._client._client = type("Client", (), {"models": models})()

    await adapter.diagnose_health("Monstera deliciosa", [])

    config = models.calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema.__name__ == "HealthDiagnosisSchema"
