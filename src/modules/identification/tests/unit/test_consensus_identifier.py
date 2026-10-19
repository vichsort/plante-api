import asyncio

import pytest

from src.modules.catalog import ImageSource
from src.modules.identification.adapters.consensus import identifier as consensus_module
from src.modules.identification.adapters.consensus.identifier import ConsensusIdentifier
from src.modules.identification.domain.exceptions import NotAPlantError
from src.modules.identification.domain.ports.plant_identifier import (
    IdentificationResult,
    IPlantIdentifier,
    SimilarImage,
)
from src.modules.identification.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from src.modules.training import (
    IdentificationProvider,
    IdentificationSignals,
    SpeciesSuggestion,
)
from src.shared.domain import ExternalServiceError, InvalidImageError

_IMAGE_SOURCES = {"kindwise": ImageSource.KINDWISE_SIMILAR, "plantnet": ImageSource.PLANTNET_SIMILAR}


class _Provider(IPlantIdentifier):
    """Responde `outcome`, ou o levanta se for uma exceção."""

    def __init__(self, outcome: IdentificationResult | Exception) -> None:
        self._outcome = outcome

    async def identify(
        self, image_bytes: bytes, latitude: float | None = None, longitude: float | None = None,
    ) -> IdentificationResult:
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


class _Slow(IPlantIdentifier):
    async def identify(
        self, image_bytes: bytes, latitude: float | None = None, longitude: float | None = None,
    ) -> IdentificationResult:
        await asyncio.sleep(1)
        raise AssertionError("o timeout deveria ter cortado antes")


def _result(
    provider: IdentificationProvider, scientific_name: str = "Monstera deliciosa", confidence: float = 0.9,
) -> IdentificationResult:
    return IdentificationResult(
        scientific_name=scientific_name,
        confidence=ConfidenceScore(confidence),
        source=provider,
        similar_images=(SimilarImage(url=f"https://{provider}/1.jpg", similarity=0.5, source=_IMAGE_SOURCES[provider]),),
        signals=(IdentificationSignals(provider=provider, suggestions=(SpeciesSuggestion(scientific_name, confidence),)),),
    )


def _consensus(kindwise: IdentificationResult | Exception, plantnet: IdentificationResult | Exception) -> ConsensusIdentifier:
    return ConsensusIdentifier(kindwise=_Provider(kindwise), plantnet=_Provider(plantnet))


_UNAVAILABLE = ExternalServiceError(service="PlantNet", retryable=True)


async def test_single_provider_failure_still_resolves() -> None:
    # Arrange
    consensus = _consensus(InvalidImageError(), _result("plantnet"))

    # Act
    result = await consensus.identify(b"img")

    # Assert
    assert result.source == "plantnet"


@pytest.mark.parametrize("plantnet", [_result("plantnet"), _UNAVAILABLE])
async def test_kindwise_not_a_plant_vetoes_plantnet(plantnet: IdentificationResult | Exception) -> None:
    # Arrange
    consensus = _consensus(NotAPlantError(), plantnet)

    # Act & Assert
    with pytest.raises(NotAPlantError):
        await consensus.identify(b"img")


async def test_invalid_image_wins_when_both_fail() -> None:
    # Arrange
    consensus = _consensus(_UNAVAILABLE, InvalidImageError())

    # Act & Assert
    with pytest.raises(InvalidImageError):
        await consensus.identify(b"img")


async def test_external_error_propagates_when_both_are_unavailable() -> None:
    # Arrange
    consensus = _consensus(_UNAVAILABLE, _UNAVAILABLE)

    # Act & Assert
    with pytest.raises(ExternalServiceError):
        await consensus.identify(b"img")


async def test_timeouts_become_external_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr(consensus_module, "_TIMEOUT_SECONDS", 0.01)
    consensus = ConsensusIdentifier(kindwise=_Slow(), plantnet=_Slow())

    # Act & Assert
    with pytest.raises(ExternalServiceError):
        await consensus.identify(b"img")


async def test_unknown_errors_keep_the_policy_behavior() -> None:
    # Arrange
    consensus = _consensus(ValueError("no suggestions"), ValueError("no results"))

    # Act & Assert
    with pytest.raises(ValueError):
        await consensus.identify(b"img")


@pytest.mark.parametrize(("kindwise", "providers"), [
    (_result("kindwise"), ["kindwise", "plantnet"]),
    (_UNAVAILABLE, ["plantnet"]),
])
async def test_keeps_the_signals_of_each_provider_that_answered(
    kindwise: IdentificationResult | Exception, providers: list[str],
) -> None:
    # Arrange
    consensus = _consensus(kindwise, _result("plantnet"))

    # Act
    result = await consensus.identify(b"img")

    # Assert
    assert [signal.provider for signal in result.signals] == providers


async def test_similar_images_come_from_kindwise_on_exact_match() -> None:
    # Arrange
    consensus = _consensus(_result("kindwise"), _result("plantnet"))

    # Act
    result = await consensus.identify(b"img")

    # Assert
    assert [img.source for img in result.similar_images] == [ImageSource.KINDWISE_SIMILAR]


async def test_similar_images_come_from_the_winning_provider() -> None:
    # Arrange
    consensus = _consensus(_result("kindwise", "Ficus lyrata", confidence=0.3), _result("plantnet", confidence=0.9))

    # Act
    result = await consensus.identify(b"img")

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    assert [img.source for img in result.similar_images] == [ImageSource.PLANTNET_SIMILAR]
