import pytest

from src.domain.policies.consensus_policy import ConsensusPolicy
from src.domain.ports.plant_identifier import IdentificationResult
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.consensus_result import ConsensusReason


def make_result(
    scientific_name: str,
    confidence: float,
    genus: str | None = None,
    family: str | None = None,
) -> IdentificationResult:
    return IdentificationResult(
        scientific_name=scientific_name,
        confidence=ConfidenceScore(confidence),
        source="test",
        genus=genus,
        family=family,
    )

def test_consensus_exact_match():
    kindwise = make_result("Monstera deliciosa", 0.90, genus="Monstera")
    plantnet = make_result("Monstera deliciosa", 0.80, genus="Monstera")

    result = ConsensusPolicy.resolve(kindwise, plantnet)

    assert result.scientific_name == "Monstera deliciosa"
    assert result.reason == ConsensusReason.EXACT_MATCH
    assert pytest.approx(result.confidence.value, 0.01) == 0.86  # 0.9*0.6 + 0.8*0.4
    assert result.low_confidence is False
    assert result.source == "consensus"

def test_consensus_genus_match():
    kindwise = make_result("Monstera deliciosa", 0.95, genus="Monstera")
    plantnet = make_result("Monstera adansonii", 0.80, genus="Monstera")

    result = ConsensusPolicy.resolve(kindwise, plantnet)

    assert result.scientific_name == "Monstera deliciosa"
    assert result.reason == ConsensusReason.GENUS_MATCH
    assert result.low_confidence is True
    assert result.source == "consensus_partial"

def test_consensus_total_disagreement_kindwise_wins():
    kindwise = make_result("Monstera deliciosa", 0.80, genus="Monstera")
    plantnet = make_result("Ficus elastica", 0.85, genus="Ficus")

    result = ConsensusPolicy.resolve(kindwise, plantnet)

    # plantnet diff é 0.05 < 0.20 threshold, então Kindwise ganha
    assert result.scientific_name == "Monstera deliciosa"
    assert result.reason == ConsensusReason.KINDWISE_OVERRIDE
    assert result.low_confidence is True
    assert result.source == "kindwise"

def test_consensus_total_disagreement_plantnet_override():
    kindwise = make_result("Monstera deliciosa", 0.50, genus="Monstera")
    plantnet = make_result("Ficus elastica", 0.80, genus="Ficus")

    result = ConsensusPolicy.resolve(kindwise, plantnet)

    # plantnet diff é 0.30 >= 0.20 threshold, então PlantNet ganha
    assert result.scientific_name == "Ficus elastica"
    assert result.reason == ConsensusReason.PLANTNET_OVERRIDE
    assert result.low_confidence is True
    assert result.source == "plantnet"

def test_consensus_single_source_fallback():
    kindwise = make_result("Monstera deliciosa", 0.85, genus="Monstera")

    result = ConsensusPolicy.resolve(kindwise, None)
    assert result.scientific_name == "Monstera deliciosa"
    assert result.reason == ConsensusReason.SINGLE_SOURCE
    assert result.source == "kindwise"

    plantnet = make_result("Ficus elastica", 0.90, genus="Ficus")
    result_p = ConsensusPolicy.resolve(None, plantnet)
    assert result_p.scientific_name == "Ficus elastica"
    assert result_p.reason == ConsensusReason.SINGLE_SOURCE
    assert result_p.source == "plantnet"

def test_consensus_both_none_raises():
    with pytest.raises(ValueError, match="Both identifiers failed"):
        ConsensusPolicy.resolve(None, None)


@pytest.mark.parametrize("kindwise, plantnet, provider", [
    (make_result("Monstera deliciosa", 0.60), make_result("Monstera deliciosa", 0.95), "kindwise"),
    (make_result("Monstera deliciosa", 0.70, genus="Monstera"),
     make_result("Monstera adansonii", 0.80, genus="Monstera"), "plantnet"),
    (make_result("Ficus lyrata", 0.30), make_result("Monstera deliciosa", 0.90), "plantnet"),
    (make_result("Ficus lyrata", 0.80), make_result("Monstera deliciosa", 0.85), "kindwise"),
    (None, make_result("Monstera deliciosa", 0.90), "plantnet"),
])
def test_consensus_reports_provider_whose_data_was_used(kindwise, plantnet, provider):
    assert ConsensusPolicy.resolve(kindwise, plantnet).provider == provider
