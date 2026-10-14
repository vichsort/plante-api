import asyncio

import pytest

from src.adapters.ai.consensus import consensus_adapter
from src.adapters.ai.consensus.consensus_adapter import ConsensusIdentifier
from src.domain.exceptions import ExternalServiceError, InvalidImageError
from src.domain.ports.plant_identifier import IdentificationResult
from src.domain.value_objects.confidence_score import ConfidenceScore


class _Identifier:
    def __init__(self, outcome) -> None:
        self._outcome = outcome

    async def identify(self, image_bytes, latitude=None, longitude=None):
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome


def _result(source: str) -> IdentificationResult:
    return IdentificationResult(
        scientific_name="Monstera deliciosa",
        confidence=ConfidenceScore(0.9),
        source=source,
    )


def _consensus(kindwise, plantnet) -> ConsensusIdentifier:
    return ConsensusIdentifier(kindwise=_Identifier(kindwise), plantnet=_Identifier(plantnet))


@pytest.mark.asyncio
async def test_single_provider_failure_still_resolves():
    result = await _consensus(InvalidImageError(), _result("plantnet")).identify(b"img")
    assert result.source == "plantnet"


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
