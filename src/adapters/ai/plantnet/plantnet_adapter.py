import base64
import httpx
from src.domain.ports.plant_identifier import IPlantIdentifier, IdentificationResult, SimilarImage
from src.domain.value_objects.confidence_score import ConfidenceScore

_BASE_URL = "https://my-api.plantnet.org/v2/identify"
_PROJECT = "all"
_NB_RESULTS = 5

class PlantNetAdapter(IPlantIdentifier):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def identify(
        self, 
        image_bytes: bytes,
        # sim, a gente só pega sem usar por que o plantnet não tem param pra isso
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        image_b64 = base64.b64encode(image_bytes).decode()
        params = {
            "api-key": self._api_key,
            "include-related-images": "true",
            "nb-results": _NB_RESULTS,
            "lang": "pt",
        }
        payload = {
            "images": [image_b64],
            "organs": ["auto"],
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}/{_PROJECT}",
                params=params,
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            return self._parse(data)

    def _parse(self, data: dict) -> IdentificationResult:
        results = data.get("results", [])
        if not results:
            raise ValueError("PlantNet returned no results.")

        best = results[0]
        species = best.get("species", {})
        taxonomy = species.get("taxonomy", {})

        common_names = tuple(species.get("commonNames", []))

        similar_images = tuple(
            SimilarImage(
                url=img.get("url", ""),
                similarity=img.get("score", 0.0),
                url_small=img.get("url2"),
                license_name=img.get("license"),
            )
            for img in best.get("images", [])
            if img.get("url")
        )

        return IdentificationResult(
            scientific_name=species.get("scientificNameWithoutAuthor", ""),
            confidence=ConfidenceScore(best.get("score", 0.0)),
            source="plantnet",
            provider_entity_id=str(taxonomy.get("gbif", {}).get("id")) if taxonomy.get("gbif") else None,
            gbif_id=str(taxonomy.get("gbif", {}).get("id")) if taxonomy.get("gbif") else None,
            family=taxonomy.get("family"),
            genus=taxonomy.get("genus"),
            common_names=common_names,
            similar_images=similar_images,
        )