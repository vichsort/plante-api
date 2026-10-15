import json

import httpx
import pytest
from google.genai import errors as genai_errors
from structlog.testing import capture_logs

from src.adapters.ai.gemini.gemini_adapter import GeminiAdapter
from src.adapters.ai.kindwise import kindwise_adapter
from src.adapters.ai.kindwise.kindwise_adapter import KindwiseAdapter
from src.adapters.ai.plantnet import plantnet_adapter
from src.adapters.ai.plantnet.plantnet_adapter import PlantNetAdapter
from src.adapters.ai.provider_errors import translate_provider_errors
from src.domain.exceptions import ExternalServiceError, InvalidImageError

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


@pytest.mark.asyncio
async def test_kindwise_adapter_translates_provider_errors(monkeypatch):
    adapter = KindwiseAdapter(api_key="test")

    _patch_transport(monkeypatch, kindwise_adapter, 400, text="Invalid image data")
    with pytest.raises(InvalidImageError):
        await adapter.identify(b"img")

    _patch_transport(monkeypatch, kindwise_adapter, 503)
    with pytest.raises(ExternalServiceError) as raised:
        await adapter.assess_health(b"img")
    assert raised.value.retryable is True


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["identify", "assess_health"])
async def test_kindwise_malformed_request_is_not_invalid_image(monkeypatch, method):
    # Kindwise também responde 400 para payload nosso malformado
    _patch_transport(monkeypatch, kindwise_adapter, 400, text="Images have to be list of base64 strings")
    with capture_logs() as logs, pytest.raises(ExternalServiceError) as raised:
        await getattr(KindwiseAdapter(api_key="test"), method)(b"img")
    assert raised.value.retryable is False
    assert any(e["event"] == "provider.request_rejected" and e["log_level"] == "error" for e in logs)


def _kindwise_body(is_plant: dict | None) -> dict:
    # Formato observado na API real (gato: probability 0.09, binary false)
    result: dict = {
        "classification": {"suggestions": [{"name": "Magnolia kobus", "probability": 0.06, "details": {}}]},
        "disease": {"suggestions": []},
        "is_healthy": {"binary": False, "probability": 0.05, "threshold": 0.5},
    }
    if is_plant is not None:
        result["is_plant"] = is_plant
    return {"status": "COMPLETED", "result": result}


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["identify", "assess_health"])
async def test_kindwise_non_plant_is_invalid_image(monkeypatch, method):
    body = _kindwise_body({"probability": 0.09, "threshold": 0.5, "binary": False})
    _patch_transport(monkeypatch, kindwise_adapter, 201, json=body)
    with pytest.raises(InvalidImageError):
        await getattr(KindwiseAdapter(api_key="test"), method)(b"img")


@pytest.mark.asyncio
@pytest.mark.parametrize("is_plant", [{"probability": 0.82, "threshold": 0.5, "binary": True}, None])
async def test_kindwise_plant_or_missing_is_plant_is_parsed(monkeypatch, is_plant):
    _patch_transport(monkeypatch, kindwise_adapter, 201, json=_kindwise_body(is_plant))
    adapter = KindwiseAdapter(api_key="test")
    assert (await adapter.identify(b"img")).scientific_name == "Magnolia kobus"
    assert (await adapter.assess_health(b"img")).is_healthy is False


@pytest.mark.asyncio
async def test_plantnet_adapter_translates_provider_errors(monkeypatch):
    _patch_transport(monkeypatch, plantnet_adapter, 429)
    with pytest.raises(ExternalServiceError) as raised:
        await PlantNetAdapter(api_key="test").identify(b"img")
    assert raised.value.retryable is True


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


@pytest.mark.asyncio
async def test_plantnet_species_not_found_is_invalid_image(monkeypatch):
    _patch_transport(monkeypatch, plantnet_adapter, 404)
    with pytest.raises(InvalidImageError):
        await PlantNetAdapter(api_key="test").identify(b"img")


@pytest.mark.asyncio
@pytest.mark.parametrize("module, adapter_cls", [(kindwise_adapter, KindwiseAdapter), (plantnet_adapter, PlantNetAdapter)])
async def test_empty_results_are_invalid_image(monkeypatch, module, adapter_cls):
    _patch_transport(monkeypatch, module, 200)
    with pytest.raises(InvalidImageError):
        await adapter_cls(api_key="test").identify(b"img")


class _FakeModels:
    def __init__(self, outcome) -> None:
        self._outcome = outcome

    def generate_content(self, **kwargs):
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return type("Response", (), {"text": self._outcome})()


def _gemini(outcome) -> GeminiAdapter:
    adapter = GeminiAdapter(api_key="test")
    adapter._client = type("Client", (), {"models": _FakeModels(outcome)})()
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


@pytest.mark.asyncio
async def test_gemini_valid_json_is_parsed():
    payload = json.dumps({"vitality_score": 0.4})
    assert (await _gemini(payload)._generate("prompt")) == {"vitality_score": 0.4}
