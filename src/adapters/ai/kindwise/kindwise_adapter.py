import httpx
from src.domain.ports.health_analyzer import IHealthAnalyzer, HealthAssessmentResult, DiseaseHint

_BASE_URL = "https://plant.id/api/v3/"

class KindwiseAdapter(IHealthAnalyzer):
    def __init__(self, api_key: str) -> None:
        self._headers = {"Api-Key": api_key}

    async def assess_health(self, image_b64: str) -> HealthAssessmentResult:
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