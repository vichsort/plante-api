"""
Chamada à API do Kindwise (plant.id v3): URL, chave e tradução de erros. Identificação e saúde usam
endpoints diferentes, cada um com o próprio adapter e contrato de resposta no módulo dono.
"""
import httpx

from src.shared.adapters.providers.errors import translate_provider_errors
from src.shared.adapters.providers.json_body import parse_json_object
from src.shared.domain import JsonObject

SERVICE = "Kindwise"
_BASE_URL = "https://plant.id/api/v3/"
# Kindwise responde 400 tanto para imagem inválida ("Invalid image data") quanto para payload
# malformado ("Images have to be list of base64 strings"); só o primeiro é erro do usuário.
# Verificado contra a API real em 2026-10-14 (identification e health_assessment).
_INVALID_IMAGE_MARKERS = ("Invalid image",)


class KindwiseClient:
    def __init__(self, api_key: str) -> None:
        self._headers = {"Api-Key": api_key}

    async def post(self, endpoint: str, payload: JsonObject, params: dict[str, str] | None = None) -> JsonObject:
        async with translate_provider_errors(SERVICE, invalid_image_markers=_INVALID_IMAGE_MARKERS), httpx.AsyncClient() as client:
            response = await client.post(
                f"{_BASE_URL}{endpoint}",
                headers=self._headers,
                params=params,
                json=payload,
            )
            response.raise_for_status()
        return parse_json_object(response.content, SERVICE)
