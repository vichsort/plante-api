import base64

import httpx

from src.adapters.ai.provider_errors import translate_provider_errors
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

_BASE_URL = "https://plant.id/api/v3/"
_DETAILS = "common_names,taxonomy,gbif_id,image,edible_parts,watering"
# Kindwise responde 400 tanto para imagem inválida ("Invalid image data") quanto para payload
# malformado ("Images have to be list of base64 strings"); só o primeiro é erro do usuário.
# Verificado contra a API real em 2026-10-14 (identification e health_assessment).
_INVALID_IMAGE_MARKERS = ("Invalid image",)

class KindwiseAdapter(IHealthAnalyzer, IPlantIdentifier):
    _headers: dict[str, str]

    def __init__(self, api_key: str) -> None:
        self._headers = {"Api-Key": api_key}

    async def identify(
        self, 
        image_bytes: bytes,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        image_b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "images": [image_b64],
            "similar_images": True,
        }
        if latitude is not None and longitude is not None:
            payload["latitude"] = latitude
            payload["longitude"] = longitude
        params = {
            "details": _DETAILS,
            "language": "pt",
        }
        async with translate_provider_errors("Kindwise", invalid_image_markers=_INVALID_IMAGE_MARKERS), httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}identification",
                headers=self._headers,
                params=params,
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            return self._parse_identification(data)

    def _parse_identification(self, data: dict) -> IdentificationResult:
        _reject_non_plant(data)
        suggestions = (
            data.get("result", {})
            .get("classification", {})
            .get("suggestions", [])
        )
        if not suggestions:
            raise InvalidImageError()

        best = suggestions[0]
        details = best.get("details", {})
        taxonomy = details.get("taxonomy", {})

        similar_images = tuple(
            SimilarImage(
                url=img.get("url", ""),
                similarity=img.get("similarity", 0.0),
                source=ImageSource.KINDWISE_SIMILAR,
                url_small=img.get("url_small"),
                license_name=img.get("license_name"),
            )
            for img in best.get("similar_images", [])
            if img.get("url")
        )

        return IdentificationResult(
            scientific_name=best.get("name", ""),
            confidence=ConfidenceScore(best.get("probability", 0.0)),
            source="kindwise",
            provider_entity_id=details.get("entity_id"),
            gbif_id=str(details["gbif_id"]) if details.get("gbif_id") else None,
            family=taxonomy.get("family"),
            genus=taxonomy.get("genus"),
            common_names=tuple(details.get("common_names") or []),
            similar_images=similar_images,
            raw_response=data,
        )

    async def assess_health(self, image_bytes: bytes) -> HealthAssessmentResult:
        image_b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "images": [image_b64],
            "similar_images": True,
        }
        async with translate_provider_errors("Kindwise", invalid_image_markers=_INVALID_IMAGE_MARKERS), httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}health_assessment",
                headers=self._headers,
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            return self._parse_health(data)

    def _parse_health(self, data: dict) -> HealthAssessmentResult:
        _reject_non_plant(data)
        result = data.get("result", {})
        is_healthy_block = result.get("is_healthy", {})

        diseases = tuple(
            DiseaseHint(
                name=d["name"],
                probability=d["probability"],
                similar_images_urls=tuple(
                    img["url"]
                    for img in d.get("similar_images", [])
                    if img.get("url")
                ),
            )
            for d in result.get("disease", {}).get("suggestions", [])
        )

        return HealthAssessmentResult(
            is_healthy=is_healthy_block.get("binary", True),
            health_probability=is_healthy_block.get("probability", 1.0),
            diseases=diseases,
            raw_response=data,
        )

def _reject_non_plant(data: dict) -> None:
    """
    Foto que não é planta volta 201 com sugestões de baixa confiança e `is_plant.binary == false`.
    Só rejeita com `false` explícito: campo ausente ou em outro formato segue o fluxo normal.
    """
    if (data.get("result") or {}).get("is_plant", {}).get("binary") is False:
        raise NotAPlantError()
