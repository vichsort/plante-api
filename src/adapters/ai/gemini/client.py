"""
Chamada ao Gemini com saída estruturada. Único ponto que toca o SDK `google-genai`, que tipa a
configuração com `dict[Any, Any]`; o resto do adapter recebe o modelo Pydantic já validado.
"""
import asyncio

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from src.adapters.ai.provider_errors import (
    provider_status_error,
    translate_provider_errors,
)
from src.adapters.ai.provider_json import parse_contract_json

SERVICE = "Gemini"
_MODEL = "gemini-2.5-flash"


class GeminiClient:
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def generate[M: BaseModel](self, prompt: str, schema: type[M]) -> M:
        try:
            # Gemini não recebe imagem: nenhum status do provedor significa imagem inválida
            async with translate_provider_errors(SERVICE, invalid_image_statuses=frozenset()):
                response = await asyncio.to_thread(
                    self._client.models.generate_content,
                    model=_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                )
        except genai_errors.APIError as exc:
            raise provider_status_error(SERVICE, exc.code) from exc

        return parse_contract_json(schema, response.text or "", SERVICE)
