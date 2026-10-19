import json

import httpx
import pytest
from pydantic import TypeAdapter
from structlog.testing import capture_logs

from src.modules.health.adapters.kindwise.analyzer import KindwiseHealthAnalyzer
from src.modules.health.tests.unit.provider_responses import load, respond_with
from src.modules.identification import NotAPlantError
from src.modules.training import HealthSignals
from src.shared.adapters import KindwiseClient
from src.shared.domain import ExternalServiceError, InvalidImageError, JsonObject


def _analyzer() -> KindwiseHealthAnalyzer:
    return KindwiseHealthAnalyzer(KindwiseClient(api_key="test"))


def _body(is_plant: JsonObject | None) -> JsonObject:
    # Formato observado na API real (gato: probability 0.09, binary false)
    result: JsonObject = {
        "disease": {"suggestions": [{"name": "leaf_spots", "probability": 0.7, "similar_images": [{"url": "https://kindwise.test/1.jpg"}]}]},
        "is_healthy": {"binary": False, "probability": 0.05, "threshold": 0.5},
    }
    if is_plant is not None:
        result["is_plant"] = is_plant
    return {"status": "COMPLETED", "result": result}


async def test_sends_the_image_and_asks_for_similar_images(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    sent = respond_with(monkeypatch, httpx.Response(201, json=_body(None)))

    # Act
    result = await _analyzer().assess_health(b"img")

    # Assert
    (request,) = sent
    assert request.url.path.endswith("/health_assessment")
    assert json.loads(request.content)["similar_images"] is True
    assert (result.is_healthy, result.health_probability) == (False, 0.05)
    assert [(d.name, d.similar_images_urls) for d in result.diseases] == [("leaf_spots", ("https://kindwise.test/1.jpg",))]


@pytest.mark.parametrize("is_plant", [{"probability": 0.82, "threshold": 0.5, "binary": True}, None])
async def test_plant_or_missing_is_plant_is_parsed(monkeypatch: pytest.MonkeyPatch, is_plant: JsonObject | None) -> None:
    # Arrange: sem o veredito explícito, segue o fluxo normal
    respond_with(monkeypatch, httpx.Response(201, json=_body(is_plant)))

    # Act
    result = await _analyzer().assess_health(b"img")

    # Assert
    assert result.is_healthy is False


async def test_non_plant_verdict_is_not_a_plant(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(201, json=_body({"probability": 0.09, "threshold": 0.5, "binary": False})))

    # Act & Assert
    with pytest.raises(NotAPlantError):
        await _analyzer().assess_health(b"img")


def test_rejects_a_real_non_plant() -> None:
    # Arrange
    data = load("kindwise/health_assessment_cat.json")

    # Act & Assert
    with pytest.raises(NotAPlantError):
        _analyzer()._parse(data)


async def test_invalid_image_answer_is_invalid_image(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(400, text="Invalid image data"))

    # Act & Assert
    with pytest.raises(InvalidImageError):
        await _analyzer().assess_health(b"img")


async def test_malformed_request_is_our_bug_not_an_invalid_image(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: o Kindwise também responde 400 para payload nosso malformado
    respond_with(monkeypatch, httpx.Response(400, text="Images have to be list of base64 strings"))

    # Act
    with capture_logs() as logs, pytest.raises(ExternalServiceError) as raised:
        await _analyzer().assess_health(b"img")

    # Assert
    assert raised.value.retryable is False
    assert any(e["event"] == "provider.request_rejected" and e["log_level"] == "error" for e in logs)


async def test_unavailable_provider_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(503, json={}))

    # Act & Assert
    with pytest.raises(ExternalServiceError) as raised:
        await _analyzer().assess_health(b"img")
    assert raised.value.retryable is True


# O Kindwise ecoa dados da requisição e da conta: os marcadores injetados na resposta real não
# podem aparecer nos sinais que viram dado de treino.
_SECRETS: dict[str, str | float] = {
    "access_token": "SECRET-ACCESS-TOKEN",
    "custom_id": "user-1234",
    "latitude": -23.5617123,
    "longitude": -46.6559876,
    "image": "https://provider/uploads/user-photo.jpg",
    "created": 1792022875.886233,
}


def test_training_signals_keep_only_training_data() -> None:
    # Arrange: a resposta real do gato, como se fosse planta, com os dados da conta e da requisição
    data = load("kindwise/health_assessment_cat.json")
    result = data["result"]
    assert isinstance(result, dict) and isinstance(result["is_plant"], dict)
    data["result"] = {**result, "is_plant": {**result["is_plant"], "binary": True}}
    data |= {"access_token": _SECRETS["access_token"], "custom_id": _SECRETS["custom_id"], "created": _SECRETS["created"]}
    echoed = data["input"]
    assert isinstance(echoed, dict)
    data["input"] = {**echoed, "latitude": _SECRETS["latitude"], "longitude": _SECRETS["longitude"], "images": [_SECRETS["image"]]}

    # Act
    signals = _analyzer()._parse(data).signals

    # Assert
    disease = result["disease"]
    assert isinstance(disease, dict) and isinstance(disease["suggestions"], list)
    assert [d.name for d in signals.diseases] == [s["name"] for s in disease["suggestions"] if isinstance(s, dict)]
    assert signals.model_version == data["model_version"]
    serialized = TypeAdapter(HealthSignals).dump_json(signals).decode()
    for name, value in _SECRETS.items():
        assert str(value) not in serialized, f"{name} vazou para os sinais de treino"
