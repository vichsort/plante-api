from typing import Any

import httpx

from src.adapters.ai.provider_errors import translate_provider_errors
from src.domain.exceptions import InvalidImageError
from src.domain.ports.plant_identifier import (
    IdentificationResult,
    IPlantIdentifier,
    SimilarImage,
)
from src.domain.value_objects.confidence_score import ConfidenceScore

_BASE_URL = "https://my-api.plantnet.org/v2/identify"
_PROJECT = "all"
_NB_RESULTS = 5
# PlantNet responde 404 "Species not found" para imagens que não são planta ou sem espécie prevista.
# 400 é ambíguo: arquivo que não é imagem ("Unsupported file type for image[0]") e payload nosso
# malformado ("\"organs\" must be one of [...]"); só o primeiro é erro do usuário.
# Verificado contra a API real em 2026-10-14. Só aceita multipart/form-data (JSON → 415).
_INVALID_IMAGE_STATUSES = frozenset({400, 404})
_INVALID_IMAGE_MARKERS = ("Unsupported file type", "Species not found")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

class PlantNetAdapter(IPlantIdentifier):
    _api_key: str

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def identify(
        self, 
        image_bytes: bytes,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        params: dict[str, Any] = {
            "api-key": self._api_key,
            "include-related-images": "true",
            "nb-results": _NB_RESULTS,
            "lang": "pt",
        }
        content_type = "image/png" if image_bytes.startswith(_PNG_SIGNATURE) else "image/jpeg"
        files = [("images", ("image", image_bytes, content_type))]
        async with translate_provider_errors(
            "PlantNet", _INVALID_IMAGE_STATUSES, invalid_image_markers=_INVALID_IMAGE_MARKERS
        ), httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}/{_PROJECT}",
                params=params,
                files=files,
                data={"organs": "auto"},
            )
            r.raise_for_status()
            data = r.json()
            return self._parse(data)

    def _parse(self, data: dict) -> IdentificationResult:
        results = data.get("results", [])
        if not results:
            raise InvalidImageError()

        best = results[0]
        species = best.get("species", {})
        gbif_id = (best.get("gbif") or {}).get("id")

        common_names = tuple(species.get("commonNames", []))

        # PlantNet não dá score por imagem de referência; `url` traz tamanhos o/m/s
        similar_images = tuple(
            SimilarImage(
                url=urls["m"],
                similarity=0.0,
                url_small=urls.get("s"),
                license_name=img.get("license"),
            )
            for img in best.get("images", [])
            if isinstance(urls := img.get("url"), dict) and urls.get("m")
        )

        return IdentificationResult(
            scientific_name=species.get("scientificNameWithoutAuthor", ""),
            confidence=ConfidenceScore(best.get("score", 0.0)),
            source="plantnet",
            provider_entity_id=str(gbif_id) if gbif_id else None,
            gbif_id=str(gbif_id) if gbif_id else None,
            family=_taxon_name(species.get("family")),
            genus=_taxon_name(species.get("genus")),
            common_names=common_names,
            similar_images=similar_images,
            raw_response=data,
        )


def _taxon_name(taxon: dict | None) -> str | None:
    return (taxon or {}).get("scientificNameWithoutAuthor") or None
