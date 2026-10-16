import json

import httpx
import pytest
from google.genai import errors as genai_errors
from structlog.testing import capture_logs

from src.adapters.ai.gemini.gemini_adapter import GeminiHealthEnricher
from src.adapters.ai.kindwise import kindwise_adapter
from src.adapters.ai.kindwise.kindwise_adapter import KindwiseAdapter
from src.adapters.ai.plantnet import plantnet_adapter
from src.adapters.ai.plantnet.plantnet_adapter import PlantNetAdapter
from src.shared.adapters import translate_provider_errors
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
    # Resposta real para foto de gato
    body = {"statusCode": 404, "error": "Not Found", "message": "Species not found"}
    _patch_transport(monkeypatch, plantnet_adapter, 404, json=body)
    with pytest.raises(InvalidImageError):
        await PlantNetAdapter(api_key="test").identify(b"img")


@pytest.mark.asyncio
async def test_plantnet_unsupported_file_is_invalid_image(monkeypatch):
    body = {"statusCode": 400, "error": "Bad Request", "message": "Unsupported file type for image[0] (jpeg or png)"}
    _patch_transport(monkeypatch, plantnet_adapter, 400, json=body)
    with pytest.raises(InvalidImageError):
        await PlantNetAdapter(api_key="test").identify(b"img")


@pytest.mark.asyncio
@pytest.mark.parametrize("status, message", [
    (400, '"organs" must be one of [auto, leaf, flower]'),
    (404, "Not Found"),
])
async def test_plantnet_rejected_request_is_not_invalid_image(monkeypatch, status, message):
    _patch_transport(monkeypatch, plantnet_adapter, status, json={"statusCode": status, "message": message})
    with capture_logs() as logs, pytest.raises(ExternalServiceError) as raised:
        await PlantNetAdapter(api_key="test").identify(b"img")
    assert raised.value.retryable is False
    assert any(e["event"] == "provider.request_rejected" for e in logs)


@pytest.mark.asyncio
@pytest.mark.parametrize("image, content_type", [
    (b"\xff\xd8\xffjpeg-bytes", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\npng-bytes", "image/png"),
])
async def test_plantnet_sends_multipart_upload(monkeypatch, image, content_type):
    # PlantNet responde 415 para JSON: a imagem precisa ir como multipart/form-data
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"results": [{"score": 0.86, "species": {"scientificNameWithoutAuthor": "Monstera deliciosa"}}]})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(plantnet_adapter.httpx, "AsyncClient", lambda: _RealAsyncClient(transport=transport))

    result = await PlantNetAdapter(api_key="test").identify(image)

    assert result.scientific_name == "Monstera deliciosa"
    request = sent[0]
    assert request.headers["content-type"].startswith("multipart/form-data")
    body = request.read()
    assert image in body
    assert f"Content-Type: {content_type}".encode() in body
    assert b'name="organs"\r\n\r\nauto' in body


_EMPTY_RESULTS = [
    (kindwise_adapter, KindwiseAdapter, {"result": {"classification": {"suggestions": []}}}),
    (plantnet_adapter, PlantNetAdapter, {"results": []}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("module, adapter_cls, body", _EMPTY_RESULTS)
async def test_empty_results_are_invalid_image(monkeypatch, module, adapter_cls, body):
    _patch_transport(monkeypatch, module, 200, json=body)
    with pytest.raises(InvalidImageError):
        await adapter_cls(api_key="test").identify(b"img")


@pytest.mark.asyncio
@pytest.mark.parametrize("module, adapter_cls, body", [
    (kindwise_adapter, KindwiseAdapter, {"result": "unexpected"}),
    (kindwise_adapter, KindwiseAdapter, [1, 2]),
    (plantnet_adapter, PlantNetAdapter, {"results": [{"score": "high"}]}),
    (plantnet_adapter, PlantNetAdapter, [1, 2]),
])
async def test_response_outside_contract_is_provider_failure(monkeypatch, module, adapter_cls, body):
    _patch_transport(monkeypatch, module, 200, json=body)
    with pytest.raises(ExternalServiceError) as raised:
        await adapter_cls(api_key="test").identify(b"img")
    assert raised.value.retryable is False


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


def test_plantnet_parses_real_response_shape():
    # Trecho da resposta real para Monstera deliciosa (2026-10-14)
    data = {
        "results": [{
            "score": 0.85787,
            "species": {
                "scientificNameWithoutAuthor": "Monstera deliciosa",
                "genus": {"scientificNameWithoutAuthor": "Monstera"},
                "family": {"scientificNameWithoutAuthor": "Araceae"},
                "commonNames": ["Costela de-adão", "Banana de-macaco"],
            },
            "images": [{
                "organ": "leaf",
                "license": "cc-by-sa",
                "url": {"o": "https://bs.plantnet.org/image/o/abc", "m": "https://bs.plantnet.org/image/m/abc",
                        "s": "https://bs.plantnet.org/image/s/abc"},
            }],
            "gbif": {"id": "2868241"},
        }],
    }

    result = PlantNetAdapter(api_key="test")._parse(data)

    assert result.scientific_name == "Monstera deliciosa"
    assert result.family == "Araceae"
    assert result.genus == "Monstera"
    assert result.gbif_id == "2868241"
    assert result.common_names == ("Costela de-adão", "Banana de-macaco")
    assert result.similar_images[0].url == "https://bs.plantnet.org/image/m/abc"
    assert result.similar_images[0].url_small == "https://bs.plantnet.org/image/s/abc"
