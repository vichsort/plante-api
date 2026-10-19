"""Respostas reais do Kindwise na avaliação de saúde (as de identificação são testadas no módulo identification)."""
import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from src.adapters.ai.kindwise.kindwise_adapter import KindwiseHealthAnalyzer
from src.modules.identification import NotAPlantError
from src.shared.adapters import KindwiseClient

_FIXTURES = Path(__file__).parents[2] / "fixtures" / "providers"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


def _analyzer() -> KindwiseHealthAnalyzer:
    return KindwiseHealthAnalyzer(KindwiseClient(api_key="test"))


def test_kindwise_health_rejects_real_non_plant():
    with pytest.raises(NotAPlantError):
        _analyzer()._parse(_load("kindwise/health_assessment_cat.json"))


# O Kindwise ecoa dados da requisição e da conta: os marcadores injetados na resposta real não
# podem aparecer nos sinais que viram dado de treino.
_SECRETS = {
    "access_token": "SECRET-ACCESS-TOKEN",
    "custom_id": "user-1234",
    "latitude": -23.5617123,
    "longitude": -46.6559876,
    "image": "https://provider/uploads/user-photo.jpg",
    "created": 1792022875.886233,
}


def test_kindwise_health_signals_keep_only_training_data():
    data = _load("kindwise/health_assessment_cat.json")
    data["result"] = {**data["result"], "is_plant": {**data["result"]["is_plant"], "binary": True}}
    data |= {"access_token": _SECRETS["access_token"], "custom_id": _SECRETS["custom_id"], "created": _SECRETS["created"]}
    data["input"] = {
        **data["input"], "latitude": _SECRETS["latitude"], "longitude": _SECRETS["longitude"], "images": [_SECRETS["image"]],
    }

    signals = _analyzer()._parse(data).signals

    assert [d.name for d in signals.diseases] == [s["name"] for s in data["result"]["disease"]["suggestions"]]
    assert signals.model_version == data["model_version"]
    serialized = TypeAdapter(type(signals)).dump_json(signals).decode()
    for name, value in _SECRETS.items():
        assert str(value) not in serialized, f"{name} vazou para os sinais de treino"
