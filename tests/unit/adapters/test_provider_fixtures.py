import json
from pathlib import Path

import pytest

from src.adapters.ai.kindwise.kindwise_adapter import KindwiseAdapter
from src.adapters.ai.plantnet.plantnet_adapter import PlantNetAdapter
from src.domain.exceptions import NotAPlantError

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
