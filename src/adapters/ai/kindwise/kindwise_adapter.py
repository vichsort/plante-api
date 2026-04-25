import httpx
from src.domain.ports.plant_identifier import IPlantIdentifier, IdentificationResult, SimilarImage
from src.domain.ports.health_analyzer import IHealthAnalyzer, HealthAssessmentResult, DiseaseHint

_BASE_URL = "https://plant.id/api/v3/"

class KindwiseAdapter(IPlantIdentifier, IHealthAnalyzer):

    def __init__(self, api_key: str) -> None:
        self._headers = {"Api-Key": api_key, "Content-Type": "application/json"}

    async def identify(self, image_bytes: bytes) -> IdentificationResult:
        import base64
        image_b64 = base64.b64encode(image_bytes).decode()
        payload = {"images": [image_b64], "similar_images": True}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}identification",
                headers=self._headers,
                json=payload,
            )
            r.raise_for_status()
            return self._parse_identification(r.json())

    async def search_by_name(self, scientific_name: str) -> IdentificationResult | None:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{_BASE_URL}kb/plants",
                headers=self._headers,
                params={"q": scientific_name, "limit": 1},
            )
            r.raise_for_status()
            results = r.json().get("entities", [])
            if not results:
                return None
            return self._parse_identification(results[0])

    async def assess_health(self, image_b64: str) -> HealthAssessmentResult:
        payload = {"images": [image_b64], "similar_images": False}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}health_assessment",
                headers=self._headers,
                json=payload,
            )
            r.raise_for_status()
            return self._parse_health(r.json())

    def _parse_identification(self, data: dict) -> IdentificationResult:
        suggestion = data.get("result", {}).get("classification", {}).get("suggestions", [{}])[0]
        similar_images = tuple(
            SimilarImage(
                url=img["url"],
                similarity=img.get("similarity", 0.0),
                url_small=img.get("url_small"),
                license_name=img.get("license_name"),
            )
            for img in suggestion.get("similar_images", [])
        )
        return IdentificationResult(
            scientific_name=suggestion.get("name", ""),
            confidence=suggestion.get("probability", 0.0),
            source="kindwise",
            similar_images=similar_images,
        )

    def _parse_health(self, data: dict) -> HealthAssessmentResult:
        result = data.get("result", {})
        is_healthy = result.get("is_healthy", {})
        diseases = tuple(
            DiseaseHint(
                name=d["name"],
                probability=d["probability"],
            )
            for d in result.get("disease", {}).get("suggestions", [])
        )
        return HealthAssessmentResult(
            is_healthy=is_healthy.get("binary", True),
            health_probability=is_healthy.get("probability", 1.0),
            diseases=diseases,
        )