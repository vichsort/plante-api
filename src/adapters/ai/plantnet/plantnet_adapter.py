import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.adapters.ai.provider_errors import translate_provider_errors
from src.adapters.ai.provider_json import parse_contract, parse_json_object
from src.domain.entities.plant_reference_image import ImageSource
from src.domain.exceptions import InvalidImageError
from src.domain.ports.plant_identifier import (
    IdentificationResult,
    IPlantIdentifier,
    SimilarImage,
)
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.json_value import JsonObject

_SERVICE = "PlantNet"

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


# Contrato da API (PlantNet v2 identify), só com os campos usados; o resto vai no raw_response.
class _Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class _Taxon(_Model):
    scientific_name_without_author: str = Field(alias="scientificNameWithoutAuthor")


class _Species(_Model):
    scientific_name_without_author: str = Field(alias="scientificNameWithoutAuthor")
    genus: _Taxon | None = None
    family: _Taxon | None = None
    common_names: tuple[str, ...] = Field(default=(), alias="commonNames")


class _Gbif(_Model):
    id: str


class _ImageUrls(_Model):
    """URLs de uma imagem de referência por tamanho: original, média e pequena."""
    o: str | None = None
    m: str | None = None
    s: str | None = None


class _Image(_Model):
    url: _ImageUrls
    license: str | None = None


class _Result(_Model):
    score: float
    species: _Species
    gbif: _Gbif | None = None
    images: list[_Image] = []


class _IdentifyResponse(_Model):
    results: list[_Result] = []


class PlantNetAdapter(IPlantIdentifier):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def identify(
        self,
        image_bytes: bytes,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        params = {
            "api-key": self._api_key,
            "include-related-images": "true",
            "nb-results": str(_NB_RESULTS),
            "lang": "pt",
        }
        content_type = "image/png" if image_bytes.startswith(_PNG_SIGNATURE) else "image/jpeg"
        files = [("images", ("image", image_bytes, content_type))]
        form = {"organs": "auto"}
        async with translate_provider_errors(
            _SERVICE, _INVALID_IMAGE_STATUSES, invalid_image_markers=_INVALID_IMAGE_MARKERS
        ), httpx.AsyncClient() as client:
            r = await client.post(
                f"{_BASE_URL}/{_PROJECT}",
                params=params,
                files=files,
                data=form,
            )
            r.raise_for_status()
        return self._parse(parse_json_object(r.content, _SERVICE))

    def _parse(self, data: JsonObject) -> IdentificationResult:
        response = parse_contract(_IdentifyResponse, data, _SERVICE)
        if not response.results:
            raise InvalidImageError()

        best = response.results[0]
        gbif_id = best.gbif.id if best.gbif else None

        return IdentificationResult(
            scientific_name=best.species.scientific_name_without_author,
            confidence=ConfidenceScore(best.score),
            source="plantnet",
            provider_entity_id=gbif_id,
            gbif_id=gbif_id,
            family=best.species.family.scientific_name_without_author if best.species.family else None,
            genus=best.species.genus.scientific_name_without_author if best.species.genus else None,
            common_names=best.species.common_names,
            # PlantNet não dá score por imagem de referência; `url` traz tamanhos o/m/s
            similar_images=tuple(
                SimilarImage(
                    url=img.url.m,
                    similarity=0.0,
                    source=ImageSource.PLANTNET_SIMILAR,
                    url_small=img.url.s,
                    license_name=img.license,
                )
                for img in best.images
                if img.url.m
            ),
            raw_response=data,
        )
