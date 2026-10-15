"""
Testes de contrato contra as APIs reais dos provedores (fora do CI e da execução padrão).

Rodar com `pytest -m contract`. Cada rodada consome ~2 créditos do Kindwise e ~2 requisições da
cota diária do PlantNet. Imagens: as mesmas de `tests/fixtures/providers/README.md`, baixadas na hora.
Provedor sem chave configurada (`KINDWISE_API_KEY` / `PLANTNET_API_KEY`) é pulado.
"""
import httpx
import pytest

from src.adapters.ai.kindwise.kindwise_adapter import KindwiseAdapter
from src.adapters.ai.plantnet.plantnet_adapter import PlantNetAdapter
from src.domain.exceptions import InvalidImageError, NotAPlantError
from src.infrastructure.settings import Settings

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
def kindwise() -> KindwiseAdapter:
    api_key = Settings().kindwise_api_key
    if not api_key:
        pytest.skip("KINDWISE_API_KEY não configurada")
    return KindwiseAdapter(api_key=api_key)


@pytest.fixture(scope="module")
def plantnet() -> PlantNetAdapter:
    api_key = Settings().plantnet_api_key
    if not api_key:
        pytest.skip("PLANTNET_API_KEY não configurada")
    return PlantNetAdapter(api_key=api_key)


async def test_kindwise_identifies_plant(kindwise: KindwiseAdapter, monstera: bytes) -> None:
    result = await kindwise.identify(monstera)
    assert result.scientific_name == "Monstera deliciosa"
    assert result.similar_images
    assert result.raw_response["result"]["is_plant"]["binary"] is True


async def test_kindwise_rejects_non_plant(kindwise: KindwiseAdapter, cat: bytes) -> None:
    with pytest.raises(NotAPlantError):
        await kindwise.identify(cat)


async def test_plantnet_identifies_plant(plantnet: PlantNetAdapter, monstera: bytes) -> None:
    result = await plantnet.identify(monstera)
    assert result.scientific_name == "Monstera deliciosa"
    assert result.family == "Araceae"
    assert result.gbif_id
    assert result.similar_images


async def test_plantnet_rejects_non_plant(plantnet: PlantNetAdapter, cat: bytes) -> None:
    with pytest.raises(InvalidImageError):
        await plantnet.identify(cat)


async def test_plantnet_rejects_non_image(plantnet: PlantNetAdapter) -> None:
    with pytest.raises(InvalidImageError):
        await plantnet.identify(b"not an image")
