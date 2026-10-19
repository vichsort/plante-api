import base64

from pydantic import BaseModel, ConfigDict, Field

from src.domain.ports.health_analyzer import (
    DiseaseHint,
    HealthAssessmentResult,
    IHealthAnalyzer,
)
from src.modules.identification import NotAPlantError
from src.modules.training import DiseaseSuggestion, HealthSignals
from src.shared.adapters import KindwiseClient, parse_contract
from src.shared.domain import JsonObject

_SERVICE = "Kindwise"


# Contrato da API (plant.id v3, `/health_assessment`), só com os campos usados. O resto da resposta
# é descartado: ela ecoa a requisição (`input` com coordenadas e URL da foto), traz `access_token`
# (dá acesso à avaliação, com a foto, na API deles) e horários — nada disso pode chegar ao dataset.
class _Model(BaseModel):
    # `model_version` é campo da API: libera o prefixo `model_` reservado pelo Pydantic
    model_config = ConfigDict(frozen=True, protected_namespaces=())


class _BinaryVerdict(_Model):
    binary: bool
    probability: float


class _SimilarImage(_Model):
    url: str


class _Suggestion(_Model):
    name: str
    probability: float
    similar_images: list[_SimilarImage] = []


class _Suggestions(_Model):
    suggestions: list[_Suggestion] = []


class _HealthResult(_Model):
    is_plant: _BinaryVerdict | None = None
    is_healthy: _BinaryVerdict | None = None
    disease: _Suggestions = Field(default_factory=_Suggestions)


class _HealthResponse(_Model):
    result: _HealthResult
    model_version: str | None = None


class KindwiseHealthAnalyzer(IHealthAnalyzer):
    def __init__(self, client: KindwiseClient) -> None:
        self._client = client

    async def assess_health(self, image_bytes: bytes) -> HealthAssessmentResult:
        payload: JsonObject = {
            "images": [base64.b64encode(image_bytes).decode()],
            "similar_images": True,
        }
        return self._parse(await self._client.post("health_assessment", payload))

    def _parse(self, data: JsonObject) -> HealthAssessmentResult:
        response = parse_contract(_HealthResponse, data, _SERVICE)
        result = response.result
        # Foto que não é planta volta 201 com `is_plant.binary == false`; sem o campo, segue o fluxo
        if result.is_plant is not None and not result.is_plant.binary:
            raise NotAPlantError()
        health_probability = result.is_healthy.probability if result.is_healthy else 1.0

        return HealthAssessmentResult(
            is_healthy=result.is_healthy.binary if result.is_healthy else True,
            health_probability=health_probability,
            diseases=tuple(
                DiseaseHint(
                    name=suggestion.name,
                    probability=suggestion.probability,
                    similar_images_urls=tuple(img.url for img in suggestion.similar_images if img.url),
                )
                for suggestion in result.disease.suggestions
            ),
            signals=HealthSignals(
                provider="kindwise",
                is_healthy_probability=health_probability,
                diseases=tuple(
                    DiseaseSuggestion(name=suggestion.name, probability=suggestion.probability)
                    for suggestion in result.disease.suggestions
                ),
                is_plant_probability=result.is_plant.probability if result.is_plant else None,
                model_version=response.model_version,
            ),
        )
