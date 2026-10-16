import asyncio

import pytest

from src.adapters.ai.consensus import consensus_adapter
from src.adapters.ai.consensus.consensus_adapter import ConsensusIdentifier
from src.domain.entities.plant_reference_image import ImageSource
from src.domain.exceptions import NotAPlantError
from src.domain.ports.plant_identifier import IdentificationResult, SimilarImage
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.provider_signals import (
    IdentificationSignals,
    SpeciesSuggestion,
)
from src.shared.domain import ExternalServiceError, InvalidImageError


class _Identifier:
    def __init__(self, outcome) -> None:
        self._outcome = outcome

    async def identify(self, image_bytes, latitude=None, longitude=None):
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome


_IMAGE_SOURCES = {"kindwise": ImageSource.KINDWISE_SIMILAR, "plantnet": ImageSource.PLANTNET_SIMILAR}


def _result(source: str, scientific_name: str = "Monstera deliciosa", confidence: float = 0.9) -> IdentificationResult:
    return IdentificationResult(
        scientific_name=scientific_name,
        confidence=ConfidenceScore(confidence),
        source=source,
        similar_images=(SimilarImage(url=f"https://{source}/1.jpg", similarity=0.5, source=_IMAGE_SOURCES[source]),),
        signals=(IdentificationSignals(provider=source, suggestions=(SpeciesSuggestion(scientific_name, confidence),)),),
    )


def _consensus(kindwise, plantnet) -> ConsensusIdentifier:
    return ConsensusIdentifier(kindwise=_Identifier(kindwise), plantnet=_Identifier(plantnet))


@pytest.mark.asyncio
async def test_single_provider_failure_still_resolves():
    result = await _consensus(InvalidImageError(), _result("plantnet")).identify(b"img")
    assert result.source == "plantnet"


@pytest.mark.asyncio
async def test_kindwise_not_a_plant_vetoes_plantnet():
    with pytest.raises(NotAPlantError):
        await _consensus(NotAPlantError(), _result("plantnet")).identify(b"img")


@pytest.mark.asyncio
async def test_not_a_plant_wins_over_plantnet_unavailable():
    unavailable = ExternalServiceError(service="PlantNet", retryable=True)
    with pytest.raises(NotAPlantError):
        await _consensus(NotAPlantError(), unavailable).identify(b"img")


@pytest.mark.asyncio
async def test_invalid_image_wins_when_both_fail():
    unavailable = ExternalServiceError(service="PlantNet", retryable=True)
    with pytest.raises(InvalidImageError):
        await _consensus(unavailable, InvalidImageError()).identify(b"img")


@pytest.mark.asyncio
async def test_external_error_propagates_when_both_unavailable():
    unavailable = ExternalServiceError(service="Kindwise", retryable=True)
    with pytest.raises(ExternalServiceError):
        await _consensus(unavailable, unavailable).identify(b"img")


@pytest.mark.asyncio
async def test_timeouts_become_external_service_error(monkeypatch):
    monkeypatch.setattr(consensus_adapter, "_TIMEOUT_SECONDS", 0.01)

    class _Slow:
        async def identify(self, image_bytes, latitude=None, longitude=None):
            await asyncio.sleep(1)

    with pytest.raises(ExternalServiceError):
        await ConsensusIdentifier(kindwise=_Slow(), plantnet=_Slow()).identify(b"img")


@pytest.mark.asyncio
async def test_unknown_errors_keep_policy_behavior():
    with pytest.raises(ValueError):
        await _consensus(ValueError("no suggestions"), ValueError("no results")).identify(b"img")


@pytest.mark.asyncio
async def test_keeps_signals_from_both_providers():
    result = await _consensus(_result("kindwise"), _result("plantnet")).identify(b"img")
    assert [signal.provider for signal in result.signals] == ["kindwise", "plantnet"]


@pytest.mark.asyncio
async def test_failed_provider_has_no_signals():
    unavailable = ExternalServiceError(service="Kindwise", retryable=True)
    result = await _consensus(unavailable, _result("plantnet")).identify(b"img")
    assert [signal.provider for signal in result.signals] == ["plantnet"]


@pytest.mark.asyncio
async def test_similar_images_come_from_kindwise_on_exact_match():
    result = await _consensus(_result("kindwise"), _result("plantnet")).identify(b"img")
    assert [img.source for img in result.similar_images] == [ImageSource.KINDWISE_SIMILAR]


@pytest.mark.asyncio
async def test_similar_images_come_from_winning_provider():
    kindwise = _result("kindwise", "Ficus lyrata", confidence=0.3)
    plantnet = _result("plantnet", "Monstera deliciosa", confidence=0.9)
    result = await _consensus(kindwise, plantnet).identify(b"img")
    assert result.scientific_name == "Monstera deliciosa"
    assert [img.source for img in result.similar_images] == [ImageSource.PLANTNET_SIMILAR]
