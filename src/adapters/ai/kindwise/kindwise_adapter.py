import base64

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.adapters.ai.provider_errors import translate_provider_errors
from src.adapters.ai.provider_json import parse_contract, parse_json_object
from src.domain.entities.plant_reference_image import ImageSource
from src.domain.exceptions import InvalidImageError, NotAPlantError
from src.domain.ports.health_analyzer import (
    DiseaseHint,
    HealthAssessmentResult,
    IHealthAnalyzer,
)
from src.domain.ports.plant_identifier import (
    IdentificationResult,
    IPlantIdentifier,
    SimilarImage,
)
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.json_value import JsonObject

_SERVICE = "Kindwise"
_BASE_URL = "https://plant.id/api/v3/"
_DETAILS = "common_names,taxonomy,gbif_id,image,edible_parts,watering"
# Kindwise responde 400 tanto para imagem inválida ("Invalid image data") quanto para payload
# malformado ("Images have to be list of base64 strings"); só o primeiro é erro do usuário.
# Verificado contra a API real em 2026-10-14 (identification e health_assessment).
_INVALID_IMAGE_MARKERS = ("Invalid image",)


# Contrato da API (plant.id v3), só com os campos usados; o resto vai inteiro no raw_response.
class _Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class _BinaryVerdict(_Model):
    binary: bool
    probability: float


class _SimilarImage(_Model):
    url: str
    similarity: float = 0.0
    url_small: str | None = None
    license_name: str | None = None


class _Taxonomy(_Model):
    family: str | None = None
    genus: str | None = None


class _Details(_Model):
    entity_id: str | None = None
    gbif_id: int | None = None
    common_names: list[str] | None = None
    taxonomy: _Taxonomy = Field(default_factory=_Taxonomy)


class _Suggestion(_Model):
    name: str
    probability: float
    similar_images: list[_SimilarImage] = []
    details: _Details = Field(default_factory=_Details)


class _Suggestions(_Model):
    suggestions: list[_Suggestion] = []


class _IdentificationResult(_Model):
    is_plant: _BinaryVerdict | None = None
    classification: _Suggestions = Field(default_factory=_Suggestions)


class _IdentificationResponse(_Model):
    result: _IdentificationResult


class _HealthResult(_Model):
    is_plant: _BinaryVerdict | None = None
    is_healthy: _BinaryVerdict | None = None
    disease: _Suggestions = Field(default_factory=_Suggestions)


class _HealthResponse(_Model):
    result: _HealthResult


class KindwiseAdapter(IHealthAnalyzer, IPlantIdentifier):
    def __init__(self, api_key: str) -> None:
        self._headers = {"Api-Key": api_key}

    async def identify(
        self,
        image_bytes: bytes,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        payload: JsonObject = {
            "images": [base64.b64encode(image_bytes).decode()],
            "similar_images": True,
        }
        if latitude is not None and longitude is not None:
            payload["latitude"] = latitude
            payload["longitude"] = longitude
        params = {
            "details": _DETAILS,
            "language": "pt",
        }
        async with translate_provider_errors(_SERVICE, invalid_image_markers=_INVALID_IMAGE_MARKERS), httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}identification",
                headers=self._headers,
                params=params,
                json=payload,
            )
            r.raise_for_status()
        return self._parse_identification(parse_json_object(r.content, _SERVICE))

    def _parse_identification(self, data: JsonObject) -> IdentificationResult:
        result = parse_contract(_IdentificationResponse, data, _SERVICE).result
        _reject_non_plant(result.is_plant)
        if not result.classification.suggestions:
            raise InvalidImageError()

        best = result.classification.suggestions[0]
        details = best.details

        return IdentificationResult(
            scientific_name=best.name,
            confidence=ConfidenceScore(best.probability),
            source="kindwise",
            provider_entity_id=details.entity_id,
            gbif_id=str(details.gbif_id) if details.gbif_id else None,
            family=details.taxonomy.family,
            genus=details.taxonomy.genus,
            common_names=tuple(details.common_names or ()),
            similar_images=tuple(
                SimilarImage(
                    url=img.url,
                    similarity=img.similarity,
                    source=ImageSource.KINDWISE_SIMILAR,
                    url_small=img.url_small,
                    license_name=img.license_name,
                )
                for img in best.similar_images
                if img.url
            ),
            raw_response=data,
        )

    async def assess_health(self, image_bytes: bytes) -> HealthAssessmentResult:
        payload: JsonObject = {
            "images": [base64.b64encode(image_bytes).decode()],
            "similar_images": True,
        }
        async with translate_provider_errors(_SERVICE, invalid_image_markers=_INVALID_IMAGE_MARKERS), httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}health_assessment",
                headers=self._headers,
                json=payload,
            )
            r.raise_for_status()
        return self._parse_health(parse_json_object(r.content, _SERVICE))

    def _parse_health(self, data: JsonObject) -> HealthAssessmentResult:
        result = parse_contract(_HealthResponse, data, _SERVICE).result
        _reject_non_plant(result.is_plant)

        return HealthAssessmentResult(
            is_healthy=result.is_healthy.binary if result.is_healthy else True,
            health_probability=result.is_healthy.probability if result.is_healthy else 1.0,
            diseases=tuple(
                DiseaseHint(
                    name=suggestion.name,
                    probability=suggestion.probability,
                    similar_images_urls=tuple(img.url for img in suggestion.similar_images if img.url),
                )
                for suggestion in result.disease.suggestions
            ),
            raw_response=data,
        )


def _reject_non_plant(is_plant: _BinaryVerdict | None) -> None:
    """
    Foto que não é planta volta 201 com sugestões de baixa confiança e `is_plant.binary == false`.
    Só rejeita com o veredito explícito: sem o campo `is_plant`, segue o fluxo normal.
    """
    if is_plant is not None and not is_plant.binary:
        raise NotAPlantError()
