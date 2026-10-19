import pytest

from src.modules.identification.domain.policies.consensus_policy import ConsensusPolicy
from src.modules.identification.domain.ports.plant_identifier import (
    IdentificationResult,
)
from src.modules.identification.domain.value_objects.consensus_result import (
    ConsensusReason,
)
from src.modules.identification.tests.fakes import make_result
from src.modules.training import IdentificationProvider


def _result(scientific_name: str, confidence: float, genus: str | None = None) -> IdentificationResult:
    return make_result(scientific_name, confidence, genus=genus)


def test_exact_match_averages_weighted_scores() -> None:
    # Arrange
    kindwise = _result("Monstera deliciosa", 0.90, genus="Monstera")
    plantnet = _result("Monstera deliciosa", 0.80, genus="Monstera")

    # Act
    result = ConsensusPolicy.resolve(kindwise, plantnet)

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    assert result.reason == ConsensusReason.EXACT_MATCH
    assert result.confidence.value == pytest.approx(0.86)  # 0.9*0.6 + 0.8*0.4
    assert result.low_confidence is False
    assert result.source == "consensus"


def test_genus_match_takes_the_highest_score_and_needs_review() -> None:
    # Arrange
    kindwise = _result("Monstera deliciosa", 0.95, genus="Monstera")
    plantnet = _result("Monstera adansonii", 0.80, genus="Monstera")

    # Act
    result = ConsensusPolicy.resolve(kindwise, plantnet)

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    assert result.reason == ConsensusReason.GENUS_MATCH
    assert result.low_confidence is True
    assert result.source == "consensus_partial"


def test_total_disagreement_keeps_kindwise_below_the_override_threshold() -> None:
    # Arrange: o PlantNet tem só 5 pontos a mais (o limiar é 20)
    kindwise = _result("Monstera deliciosa", 0.80, genus="Monstera")
    plantnet = _result("Ficus elastica", 0.85, genus="Ficus")

    # Act
    result = ConsensusPolicy.resolve(kindwise, plantnet)

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    assert result.reason == ConsensusReason.KINDWISE_OVERRIDE
    assert result.low_confidence is True
    assert result.source == "kindwise"


def test_total_disagreement_plantnet_overrides_with_a_much_higher_score() -> None:
    # Arrange: 30 pontos a mais
    kindwise = _result("Monstera deliciosa", 0.50, genus="Monstera")
    plantnet = _result("Ficus elastica", 0.80, genus="Ficus")

    # Act
    result = ConsensusPolicy.resolve(kindwise, plantnet)

    # Assert
    assert result.scientific_name == "Ficus elastica"
    assert result.reason == ConsensusReason.PLANTNET_OVERRIDE
    assert result.low_confidence is True
    assert result.source == "plantnet"


@pytest.mark.parametrize(("kindwise_answers", "source"), [(True, "kindwise"), (False, "plantnet")])
def test_single_source_decides_alone(kindwise_answers: bool, source: str) -> None:
    # Arrange
    answer = _result("Monstera deliciosa", 0.85, genus="Monstera")

    # Act
    result = ConsensusPolicy.resolve(answer, None) if kindwise_answers else ConsensusPolicy.resolve(None, answer)

    # Assert
    assert result.scientific_name == "Monstera deliciosa"
    assert result.reason == ConsensusReason.SINGLE_SOURCE
    assert result.source == source


def test_both_missing_cannot_resolve() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="Both identifiers failed"):
        ConsensusPolicy.resolve(None, None)


@pytest.mark.parametrize(("kindwise", "plantnet", "provider"), [
    (_result("Monstera deliciosa", 0.60), _result("Monstera deliciosa", 0.95), "kindwise"),
    (_result("Monstera deliciosa", 0.70, genus="Monstera"), _result("Monstera adansonii", 0.80, genus="Monstera"), "plantnet"),
    (_result("Ficus lyrata", 0.30), _result("Monstera deliciosa", 0.90), "plantnet"),
    (_result("Ficus lyrata", 0.80), _result("Monstera deliciosa", 0.85), "kindwise"),
    (None, _result("Monstera deliciosa", 0.90), "plantnet"),
])
def test_reports_the_provider_whose_data_was_used(
    kindwise: IdentificationResult | None, plantnet: IdentificationResult | None, provider: IdentificationProvider,
) -> None:
    # Act
    result = ConsensusPolicy.resolve(kindwise, plantnet)

    # Assert
    assert result.provider == provider
