import httpx
import base64
from src.domain.ports.health_analyzer import IHealthAnalyzer, HealthAssessmentResult, DiseaseHint
from src.domain.ports.plant_identifier import IPlantIdentifier, IdentificationResult, SimilarImage
from src.domain.value_objects.confidence_score import ConfidenceScore

_BASE_URL = "https://plant.id/api/v3/"
_DETAILS = "common_names,taxonomy,gbif_id,image,edible_parts,watering"

class KindwiseAdapter(IHealthAnalyzer, IPlantIdentifier):
    def __init__(self, api_key: str) -> None:
        self._headers = {"Api-Key": api_key}

    # ------------------------------------------------------------------ #
    # IPlantIdentifier                                                   #
    # ------------------------------------------------------------------ #

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
        async with httpx.AsyncClient() as client:
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
        suggestions = (
            data.get("result", {})
            .get("classification", {})
            .get("suggestions", [])
        )
        if not suggestions:
            raise ValueError("Kindwise returned no identification suggestions.")

        best = suggestions[0]
        details = best.get("details", {})
        taxonomy = details.get("taxonomy", {})

        similar_images = tuple(
            SimilarImage(
                url=img.get("url", ""),
                similarity=img.get("similarity", 0.0),
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
        )

    # ------------------------------------------------------------------ #
    # IHealthAnalyzer                                                    #
    # ------------------------------------------------------------------ #

    async def assess_health(self, image_bytes: bytes) -> HealthAssessmentResult:
        image_b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "images": [image_b64],
            "similar_images": True,
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}health_assessment",
                headers=self._headers,
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            return self._parse_health(data)

    def _parse_health(self, data: dict) -> HealthAssessmentResult:
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