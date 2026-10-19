"""
Testes de contrato contra as APIs reais dos provedores (fora do CI e da execução padrão).

Rodar com `uv run --env-file .env pytest -m contract` (as chaves vêm do ambiente: o módulo não lê o
`Settings` da composição). Cada rodada consome ~2 créditos do Kindwise e ~2 requisições da
cota diária do PlantNet. Imagens: as mesmas de `tests/fixtures/providers/README.md`, baixadas na hora.
Provedor sem chave configurada (`KINDWISE_API_KEY` / `PLANTNET_API_KEY`) é pulado.
"""
import os

import httpx
import pytest

from src.modules.identification.adapters.kindwise.identifier import KindwiseIdentifier
from src.modules.identification.adapters.plantnet.identifier import PlantNetIdentifier
from src.modules.identification.domain.exceptions import NotAPlantError
from src.shared.adapters import KindwiseClient
from src.shared.domain import InvalidImageError

pytestmark = pytest.mark.contract

_COMMONS = "https://commons.wikimedia.org/wiki/Special:FilePath/{name}?width=800"
# Wikimedia rejeita requisições sem User-Agent identificável
_USER_AGENT = "plante-api-contract-tests/1.0 (https://github.com/vichsort/plante-api)"


def _download(name: str) -> bytes:
    response = httpx.get(
        _COMMONS.format(name=name),
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.content


@pytest.fixture(scope="module")
def monstera() -> bytes:
    return _download("Monstera_deliciosa3.jpg")


@pytest.fixture(scope="module")
def cat() -> bytes:
    return _download("Cat_November_2010-1a.jpg")


@pytest.fixture(scope="module")
def kindwise() -> KindwiseIdentifier:
    api_key = os.environ.get("KINDWISE_API_KEY")
    if not api_key:
        pytest.skip("KINDWISE_API_KEY não configurada")
    return KindwiseIdentifier(KindwiseClient(api_key=api_key))


@pytest.fixture(scope="module")
def plantnet() -> PlantNetIdentifier:
    api_key = os.environ.get("PLANTNET_API_KEY")
    if not api_key:
        pytest.skip("PLANTNET_API_KEY não configurada")
    return PlantNetIdentifier(api_key=api_key)


async def test_kindwise_identifies_plant(kindwise: KindwiseIdentifier, monstera: bytes) -> None:
    # Act
    result = await kindwise.identify(monstera)

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    assert result.similar_images
    (signals,) = result.signals
    assert signals.is_plant_probability is not None and signals.is_plant_probability > 0.5
    assert signals.suggestions[0].scientific_name == "Monstera deliciosa"


async def test_kindwise_rejects_non_plant(kindwise: KindwiseIdentifier, cat: bytes) -> None:
    # Act & Assert
    with pytest.raises(NotAPlantError):
        await kindwise.identify(cat)


async def test_plantnet_identifies_plant(plantnet: PlantNetIdentifier, monstera: bytes) -> None:
    # Act
    result = await plantnet.identify(monstera)

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    assert result.family == "Araceae"
    assert result.gbif_id
    assert result.similar_images


async def test_plantnet_rejects_non_plant(plantnet: PlantNetIdentifier, cat: bytes) -> None:
    # Act & Assert
    with pytest.raises(InvalidImageError):
        await plantnet.identify(cat)


async def test_plantnet_rejects_non_image(plantnet: PlantNetIdentifier) -> None:
    # Act & Assert
    with pytest.raises(InvalidImageError):
        await plantnet.identify(b"not an image")
