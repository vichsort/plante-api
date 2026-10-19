import httpx
import pytest
from pydantic import TypeAdapter
from structlog.testing import capture_logs

from src.modules.identification.adapters.kindwise.identifier import KindwiseIdentifier
from src.modules.identification.domain.exceptions import NotAPlantError
from src.modules.identification.tests.unit.provider_responses import load, respond_with
from src.modules.training import IdentificationSignals
from src.shared.adapters import KindwiseClient
from src.shared.domain import ExternalServiceError, InvalidImageError, JsonObject


def _identifier() -> KindwiseIdentifier:
    return KindwiseIdentifier(KindwiseClient(api_key="test"))


def _body(is_plant: JsonObject | None) -> JsonObject:
    # Formato observado na API real (gato: probability 0.09, binary false)
    result: JsonObject = {"classification": {"suggestions": [{"name": "Magnolia kobus", "probability": 0.06, "details": {}}]}}
    if is_plant is not None:
        result["is_plant"] = is_plant
    return {"status": "COMPLETED", "result": result}


def test_parses_a_real_identification() -> None:
    # Arrange
    data = load("kindwise/identification_monstera.json")

    # Act
    result = _identifier()._parse(data)

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    assert result.confidence.value > 0.9


def test_rejects_a_real_non_plant() -> None:
    # Arrange
    data = load("kindwise/identification_cat.json")

    # Act & Assert
    with pytest.raises(NotAPlantError):
        _identifier()._parse(data)


@pytest.mark.parametrize("is_plant", [{"probability": 0.82, "threshold": 0.5, "binary": True}, None])
async def test_plant_or_missing_is_plant_is_parsed(monkeypatch: pytest.MonkeyPatch, is_plant: JsonObject | None) -> None:
    # Arrange: sem o veredito explícito, segue o fluxo normal
    respond_with(monkeypatch, httpx.Response(201, json=_body(is_plant)))

    # Act
    result = await _identifier().identify(b"img")

    # Assert
    assert result.scientific_name == "Magnolia kobus"


async def test_non_plant_verdict_is_invalid_image(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(201, json=_body({"probability": 0.09, "threshold": 0.5, "binary": False})))

    # Act & Assert
    with pytest.raises(NotAPlantError):
        await _identifier().identify(b"img")


async def test_invalid_image_answer_is_invalid_image(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(400, text="Invalid image data"))

    # Act & Assert
    with pytest.raises(InvalidImageError):
        await _identifier().identify(b"img")


async def test_malformed_request_is_our_bug_not_an_invalid_image(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: o Kindwise também responde 400 para payload nosso malformado
    respond_with(monkeypatch, httpx.Response(400, text="Images have to be list of base64 strings"))

    # Act
    with capture_logs() as logs, pytest.raises(ExternalServiceError) as raised:
        await _identifier().identify(b"img")

    # Assert
    assert raised.value.retryable is False
    assert any(e["event"] == "provider.request_rejected" and e["log_level"] == "error" for e in logs)


async def test_unavailable_provider_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(503, json={}))

    # Act & Assert
    with pytest.raises(ExternalServiceError) as raised:
        await _identifier().identify(b"img")
    assert raised.value.retryable is True


async def test_empty_suggestions_are_invalid_image(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(200, json={"result": {"classification": {"suggestions": []}}}))

    # Act & Assert
    with pytest.raises(InvalidImageError):
        await _identifier().identify(b"img")


@pytest.mark.parametrize("body", [{"result": "unexpected"}, [1, 2]])
async def test_response_outside_the_contract_is_a_provider_failure(monkeypatch: pytest.MonkeyPatch, body: object) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(200, json=body))

    # Act & Assert
    with pytest.raises(ExternalServiceError) as raised:
        await _identifier().identify(b"img")
    assert raised.value.retryable is False


async def test_sends_coordinates_only_when_both_are_given(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    sent = respond_with(monkeypatch, httpx.Response(201, json=_body(None)))

    # Act
    await _identifier().identify(b"img", latitude=-23.5)
    await _identifier().identify(b"img", latitude=-23.5, longitude=-46.6)

    # Assert
    assert [b"latitude" in request.read() for request in sent] == [False, True]


# --- O que chega ao dataset de treino --------------------------------------------------------
# O Kindwise ecoa dados da requisição e da conta. Os marcadores abaixo são injetados na resposta
# real; nenhum deles pode aparecer nos sinais que viram dado de treino.

_SECRETS: dict[str, str | float] = {
    "access_token": "SECRET-ACCESS-TOKEN",
    "custom_id": "user-1234",
    "latitude": -23.5617123,
    "longitude": -46.6559876,
    "image": "https://provider/uploads/user-photo.jpg",
    "created": 1792022875.886233,
}


def test_signals_keep_only_training_data() -> None:
    # Arrange
    data = load("kindwise/identification_monstera.json")
    data |= {"access_token": _SECRETS["access_token"], "custom_id": _SECRETS["custom_id"], "created": _SECRETS["created"]}
    echoed = data["input"]
    assert isinstance(echoed, dict)
    data["input"] = echoed | {
        "latitude": _SECRETS["latitude"], "longitude": _SECRETS["longitude"], "images": [str(_SECRETS["image"])],
    }

    # Act
    (signals,) = _identifier()._parse(data).signals

    # Assert
    assert signals.provider == "kindwise"
    assert signals.suggestions[0].scientific_name == "Monstera deliciosa"
    assert signals.model_version == data["model_version"]
    serialized = TypeAdapter(IdentificationSignals).dump_json(signals).decode()
    for name, value in _SECRETS.items():
        assert str(value) not in serialized, f"{name} vazou para os sinais de treino"
