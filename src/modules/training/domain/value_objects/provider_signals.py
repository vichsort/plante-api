"""
O que cada provedor de IA disse sobre uma foto, já filtrado: só o que serve para treinar e para
pesar a confiança do rótulo. Substitui a resposta bruta (`raw_response`), que ecoava dados da
requisição (coordenadas, URL da foto, `access_token` do Kindwise, horários).
"""
from dataclasses import dataclass

from src.modules.training.domain.value_objects.provenance import IdentificationProvider


@dataclass(frozen=True)
class SpeciesSuggestion:
    scientific_name: str
    probability: float
    family: str | None = None
    genus: str | None = None
    gbif_id: str | None = None
    provider_entity_id: str | None = None


@dataclass(frozen=True)
class IdentificationSignals:
    """Sugestões de um provedor em ordem de probabilidade (a primeira é a escolhida por ele)."""
    provider: IdentificationProvider
    suggestions: tuple[SpeciesSuggestion, ...]
    is_plant_probability: float | None = None
    model_version: str | None = None


@dataclass(frozen=True)
class DiseaseSuggestion:
    name: str
    probability: float


@dataclass(frozen=True)
class HealthSignals:
    provider: IdentificationProvider
    is_healthy_probability: float
    diseases: tuple[DiseaseSuggestion, ...]
    is_plant_probability: float | None = None
    model_version: str | None = None
