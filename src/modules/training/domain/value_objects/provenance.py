"""
Vocabulário de proveniência do dataset: quem produziu cada rótulo e com que severidade. Mora no
training porque é o formato das amostras; quem produz o dado (identificação, saúde) importa daqui.
"""
from enum import StrEnum
from typing import Literal

# Provedor de IA que respondeu uma identificação
IdentificationProvider = Literal["kindwise", "plantnet"]

# Origem final de uma identificação: um provedor sozinho ou o consenso entre os dois
# ("consensus_partial" = só o gênero bateu)
IdentificationOrigin = Literal["kindwise", "plantnet", "consensus", "consensus_partial"]

# Origem de um diagnóstico de saúde: só Kindwise ou Kindwise complementado pelo Gemini
HealthSource = Literal["kindwise", "kindwise+gemini"]


class HealthSeverity(StrEnum):
    HEALTHY = "healthy"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


def parse_identification_origin(value: str) -> IdentificationOrigin:
    """Texto gravado (coluna de origem) → o `Literal` do domínio; valor desconhecido é erro."""
    match value:
        case "kindwise" | "plantnet" | "consensus" | "consensus_partial":
            return value
    raise ValueError(f"Unknown identification origin: {value!r}")


def parse_health_source(value: str) -> HealthSource:
    match value:
        case "kindwise" | "kindwise+gemini":
            return value
    raise ValueError(f"Unknown health source: {value!r}")
