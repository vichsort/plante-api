"""Converte as colunas de origem (texto no banco) para os tipos `Literal` do domínio."""
from src.domain.value_objects.sources import HealthSource, IdentificationOrigin


def to_identification_origin(value: str) -> IdentificationOrigin:
    match value:
        case "kindwise" | "plantnet" | "consensus" | "consensus_partial":
            return value
    raise ValueError(f"Unknown identification origin in database: {value!r}")


def to_health_source(value: str) -> HealthSource:
    match value:
        case "kindwise" | "kindwise+gemini":
            return value
    raise ValueError(f"Unknown health source in database: {value!r}")
