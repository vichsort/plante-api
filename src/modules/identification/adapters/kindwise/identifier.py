import base64

from pydantic import BaseModel, ConfigDict, Field

from src.modules.catalog import ImageSource
from src.modules.identification.domain.exceptions import NotAPlantError
from src.modules.identification.domain.ports.plant_identifier import (
    IdentificationResult,
    IPlantIdentifier,
    SimilarImage,
)
from src.modules.identification.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from src.modules.training import IdentificationSignals, SpeciesSuggestion
from src.shared.adapters import KindwiseClient, parse_contract
from src.shared.domain import InvalidImageError, JsonObject

_SERVICE = "Kindwise"
_DETAILS = "common_names,taxonomy,gbif_id,image,edible_parts,watering"


# Contrato da API (plant.id v3, `/identification`), só com os campos usados. O resto da resposta é
# descartado: ela ecoa a requisição (`input` com coordenadas e URL da foto), traz `access_token`
# (dá acesso à identificação, com a foto, na API deles) e horários — nada disso pode chegar ao dataset.
class _Model(BaseModel):
    # `model_version` é campo da API: libera o prefixo `model_` reservado pelo Pydantic
    model_config = ConfigDict(frozen=True, protected_namespaces=())


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


class _Result(_Model):
    is_plant: _BinaryVerdict | None = None
    classification: _Suggestions = Field(default_factory=_Suggestions)


class _Response(_Model):
    result: _Result
    model_version: str | None = None


class KindwiseIdentifier(IPlantIdentifier):
    def __init__(self, client: KindwiseClient) -> None:
        self._client = client

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
        data = await self._client.post("identification", payload, params={"details": _DETAILS, "language": "pt"})
        return self._parse(data)

    def _parse(self, data: JsonObject) -> IdentificationResult:
        response = parse_contract(_Response, data, _SERVICE)
        result = response.result
        # Foto que não é planta volta 201 com sugestões de baixa confiança e `is_plant.binary == false`.
        # Só rejeita com o veredito explícito: sem o campo `is_plant`, segue o fluxo normal.
        if result.is_plant is not None and not result.is_plant.binary:
            raise NotAPlantError()
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
            signals=(IdentificationSignals(
                provider="kindwise",
                suggestions=tuple(
                    SpeciesSuggestion(
                        scientific_name=suggestion.name,
                        probability=suggestion.probability,
                        family=suggestion.details.taxonomy.family,
                        genus=suggestion.details.taxonomy.genus,
                        gbif_id=str(suggestion.details.gbif_id) if suggestion.details.gbif_id else None,
                        provider_entity_id=suggestion.details.entity_id,
                    )
                    for suggestion in result.classification.suggestions
                ),
                is_plant_probability=result.is_plant.probability if result.is_plant else None,
                model_version=response.model_version,
            ),),
        )
