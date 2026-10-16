import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from src.adapters.ai.kindwise.kindwise_adapter import KindwiseAdapter
from src.adapters.ai.plantnet.plantnet_adapter import PlantNetAdapter
from src.domain.exceptions import NotAPlantError
from src.modules.catalog import ImageSource

_FIXTURES = Path(__file__).parents[2] / "fixtures" / "providers"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


def test_kindwise_parses_real_identification():
    result = KindwiseAdapter(api_key="test")._parse_identification(_load("kindwise/identification_monstera.json"))
    assert result.scientific_name == "Monstera deliciosa"
    assert result.confidence.value > 0.9


@pytest.mark.parametrize("name, parse", [
    ("kindwise/identification_cat.json", "_parse_identification"),
    ("kindwise/health_assessment_cat.json", "_parse_health"),
])
def test_kindwise_rejects_real_non_plant(name, parse):
    with pytest.raises(NotAPlantError):
        getattr(KindwiseAdapter(api_key="test"), parse)(_load(name))


def test_plantnet_parses_real_identification():
    result = PlantNetAdapter(api_key="test")._parse(_load("plantnet/identify_monstera.json"))
    assert result.scientific_name == "Monstera deliciosa"
    assert result.family == "Araceae"
    assert result.genus == "Monstera"
    assert result.gbif_id
    assert result.similar_images
    assert {img.source for img in result.similar_images} == {ImageSource.PLANTNET_SIMILAR}


# --- O que chega ao dataset de treino --------------------------------------------------------
# Os provedores ecoam dados da requisição e da conta. Os marcadores abaixo são injetados nas
# respostas reais; nenhum deles pode aparecer nos sinais que viram dado de treino.

_SECRETS = {
    "access_token": "SECRET-ACCESS-TOKEN",
    "custom_id": "user-1234",
    "latitude": -23.5617123,
    "longitude": -46.6559876,
    "image": "https://provider/uploads/user-photo.jpg",
    "created": 1792022875.886233,
}


def _signals_json(signals: object) -> str:
    return TypeAdapter(type(signals)).dump_json(signals).decode()


def _with_echoed_request(data: dict) -> dict:
    data = dict(data)
    data["access_token"] = _SECRETS["access_token"]
    data["custom_id"] = _SECRETS["custom_id"]
    data["created"] = _SECRETS["created"]
    data["input"] = {
        **data["input"],
        "latitude": _SECRETS["latitude"],
        "longitude": _SECRETS["longitude"],
        "images": [_SECRETS["image"]],
    }
    return data


def _assert_no_secrets(serialized: str) -> None:
    for name, value in _SECRETS.items():
        assert str(value) not in serialized, f"{name} vazou para os sinais de treino"


def test_kindwise_identification_signals_keep_only_training_data():
    data = _with_echoed_request(_load("kindwise/identification_monstera.json"))

    (signals,) = KindwiseAdapter(api_key="test")._parse_identification(data).signals

    assert signals.provider == "kindwise"
    assert signals.suggestions[0].scientific_name == "Monstera deliciosa"
    assert len(signals.suggestions) == len(data["result"]["classification"]["suggestions"])
    assert signals.is_plant_probability == data["result"]["is_plant"]["probability"]
    assert signals.model_version == data["model_version"]
    _assert_no_secrets(_signals_json(signals))


def test_kindwise_health_signals_keep_only_training_data():
    data = _with_echoed_request(_load("kindwise/health_assessment_cat.json"))
    data["result"] = {**data["result"], "is_plant": {**data["result"]["is_plant"], "binary": True}}

    signals = KindwiseAdapter(api_key="test")._parse_health(data).signals

    assert [d.name for d in signals.diseases] == [s["name"] for s in data["result"]["disease"]["suggestions"]]
    assert signals.model_version == data["model_version"]
    _assert_no_secrets(_signals_json(signals))


def test_plantnet_signals_drop_query_and_account_data():
    data = dict(_load("plantnet/identify_monstera.json"))
    data["query"] = {**data["query"], "images": [_SECRETS["image"]]}

    (signals,) = PlantNetAdapter(api_key="test")._parse(data).signals

    assert signals.provider == "plantnet"
    assert len(signals.suggestions) == len(data["results"])
    assert signals.model_version == data["version"]
    serialized = _signals_json(signals)
    _assert_no_secrets(serialized)
    assert "remainingIdentificationRequests" not in serialized
