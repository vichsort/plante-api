"""Image keys, the same in every backend: moving storage is copying files, not rewriting rows."""
import uuid

import httpx

from src.shared.domain.value_objects.ids import UserId

_IDENTIFICATION_PREFIX = "identifications"
_REFERENCES_PREFIX = "species/references"
# Dataset de treino: separado das fotos dos usuários (chave nova, nunca devolvida ao cliente)
_TRAINING_PREFIX = "training/identifications"
CONTENT_TYPE = "image/jpeg"


def _sanitize(scientific_name: str) -> str:
    return scientific_name.lower().replace(" ", "_")


def user_prefix(user_id: UserId) -> str:
    # Every photo a user sends lives under their own prefix, so deleting the account deletes it all
    return f"{_IDENTIFICATION_PREFIX}/{user_id}/"


def identification_key(user_id: UserId, scientific_name: str) -> str:
    return f"{user_prefix(user_id)}{_sanitize(scientific_name)}/{uuid.uuid4()}.jpg"


def reference_key(scientific_name: str) -> str:
    return f"{_REFERENCES_PREFIX}/{_sanitize(scientific_name)}/{uuid.uuid4()}.jpg"


def training_key(scientific_name: str) -> str:
    return f"{_TRAINING_PREFIX}/{_sanitize(scientific_name)}/{uuid.uuid4()}.jpg"


async def fetch_external(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content
