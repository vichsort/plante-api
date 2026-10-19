import httpx
import pytest
from pydantic import TypeAdapter
from structlog.testing import capture_logs

from src.modules.catalog import ImageSource
from src.modules.identification.adapters.plantnet.identifier import PlantNetIdentifier
from src.modules.identification.tests.unit.provider_responses import load, respond_with
from src.modules.training import IdentificationSignals
from src.shared.domain import ExternalServiceError, InvalidImageError

_MONSTERA = {"results": [{"score": 0.86, "species": {"scientificNameWithoutAuthor": "Monstera deliciosa"}}]}


def test_parses_a_real_identification() -> None:
    # Arrange
    data = load("plantnet/identify_monstera.json")

    # Act
    result = PlantNetIdentifier(api_key="test")._parse(data)

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    assert (result.family, result.genus) == ("Araceae", "Monstera")
    assert result.gbif_id
    assert {img.source for img in result.similar_images} == {ImageSource.PLANTNET_SIMILAR}


def test_parses_names_and_image_sizes() -> None:
    # Arrange: trecho da resposta real para Monstera deliciosa (2026-10-14)
    data = {"results": [{
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
    }]}

    # Act
    result = PlantNetIdentifier(api_key="test")._parse(data)

    # Assert
    assert result.gbif_id == "2868241"
    assert result.common_names == ("Costela de-adão", "Banana de-macaco")
    assert result.similar_images[0].url == "https://bs.plantnet.org/image/m/abc"
    assert result.similar_images[0].url_small == "https://bs.plantnet.org/image/s/abc"


@pytest.mark.parametrize(("image", "content_type"), [
    (b"\xff\xd8\xffjpeg-bytes", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\npng-bytes", "image/png"),
])
async def test_sends_a_multipart_upload(monkeypatch: pytest.MonkeyPatch, image: bytes, content_type: str) -> None:
    # Arrange: o PlantNet responde 415 para JSON
    sent = respond_with(monkeypatch, httpx.Response(200, json=_MONSTERA))

    # Act
    result = await PlantNetIdentifier(api_key="test").identify(image)

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    (request,) = sent
    assert request.headers["content-type"].startswith("multipart/form-data")
    body = request.read()
    assert image in body
    assert f"Content-Type: {content_type}".encode() in body
    assert b'name="organs"\r\n\r\nauto' in body


@pytest.mark.parametrize(("status", "message"), [
    (404, "Species not found"),  # resposta real para foto de gato
    (400, "Unsupported file type for image[0] (jpeg or png)"),
])
async def test_non_plant_or_non_image_is_invalid_image(monkeypatch: pytest.MonkeyPatch, status: int, message: str) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(status, json={"statusCode": status, "message": message}))

    # Act & Assert
    with pytest.raises(InvalidImageError):
        await PlantNetIdentifier(api_key="test").identify(b"img")


@pytest.mark.parametrize(("status", "message"), [
    (400, '"organs" must be one of [auto, leaf, flower]'),
    (404, "Not Found"),
])
async def test_rejected_request_is_our_bug_not_an_invalid_image(monkeypatch: pytest.MonkeyPatch, status: int, message: str) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(status, json={"statusCode": status, "message": message}))

    # Act
    with capture_logs() as logs, pytest.raises(ExternalServiceError) as raised:
        await PlantNetIdentifier(api_key="test").identify(b"img")

    # Assert
    assert raised.value.retryable is False
    assert any(e["event"] == "provider.request_rejected" for e in logs)


async def test_rate_limit_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(429, json={}))

    # Act & Assert
    with pytest.raises(ExternalServiceError) as raised:
        await PlantNetIdentifier(api_key="test").identify(b"img")
    assert raised.value.retryable is True


async def test_empty_results_are_invalid_image(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(200, json={"results": []}))

    # Act & Assert
    with pytest.raises(InvalidImageError):
        await PlantNetIdentifier(api_key="test").identify(b"img")


@pytest.mark.parametrize("body", [{"results": [{"score": "high"}]}, [1, 2]])
async def test_response_outside_the_contract_is_a_provider_failure(monkeypatch: pytest.MonkeyPatch, body: object) -> None:
    # Arrange
    respond_with(monkeypatch, httpx.Response(200, json=body))

    # Act & Assert
    with pytest.raises(ExternalServiceError) as raised:
        await PlantNetIdentifier(api_key="test").identify(b"img")
    assert raised.value.retryable is False


def test_signals_drop_the_query_and_account_data() -> None:
    # Arrange
    data = load("plantnet/identify_monstera.json")
    query = data["query"]
    assert isinstance(query, dict)
    data["query"] = query | {"images": ["https://provider/uploads/user-photo.jpg"]}

    # Act
    (signals,) = PlantNetIdentifier(api_key="test")._parse(data).signals

    # Assert
    assert signals.provider == "plantnet"
    results = data["results"]
    assert isinstance(results, list)
    assert len(signals.suggestions) == len(results)
    assert signals.model_version == data["version"]
    serialized = TypeAdapter(IdentificationSignals).dump_json(signals).decode()
    assert "user-photo.jpg" not in serialized
    assert "remainingIdentificationRequests" not in serialized
