import uuid

import aioboto3
import httpx
import structlog
from botocore.exceptions import BotoCoreError, ClientError

from src.shared.domain.exceptions import ExternalServiceError
from src.shared.domain.ports.image_storage import IImageStorage
from src.shared.domain.value_objects.ids import UserId

logger = structlog.stdlib.get_logger()

_IDENTIFICATION_PREFIX = "identifications"
_REFERENCES_PREFIX = "species/references"
# Dataset de treino: separado das fotos dos usuários (chave nova, nunca devolvida ao cliente)
_TRAINING_PREFIX = "training/identifications"
_DEFAULT_CONTENT_TYPE = "image/jpeg"

def _sanitize(scientific_name: str) -> str:
    return scientific_name.lower().replace(" ", "_")

def _user_prefix(user_id: UserId) -> str:
    # Every photo a user sends lives under their own prefix, so deleting the account deletes it all
    return f"{_IDENTIFICATION_PREFIX}/{user_id}/"

def _build_identification_key(user_id: UserId, scientific_name: str) -> str:
    return f"{_user_prefix(user_id)}{_sanitize(scientific_name)}/{uuid.uuid4()}.jpg"

def _build_reference_key(scientific_name: str) -> str:
    return f"{_REFERENCES_PREFIX}/{_sanitize(scientific_name)}/{uuid.uuid4()}.jpg"

def _build_training_key(scientific_name: str) -> str:
    return f"{_TRAINING_PREFIX}/{_sanitize(scientific_name)}/{uuid.uuid4()}.jpg"

class S3ImageStorage(IImageStorage):
    def __init__(
        self,
        bucket_name: str,
        region: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
    ) -> None:
        self._bucket = bucket_name
        self._region = region
        self._session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region,
        )

    async def upload_identification_image(
        self,
        image_bytes: bytes,
        scientific_name: str,
        confidence_value: float,
        user_id: UserId,
    ) -> str:
        key = _build_identification_key(user_id, scientific_name)

        await self._put_object(
            key=key,
            body=image_bytes,
            content_type=_DEFAULT_CONTENT_TYPE,
        )

        url = self._public_url(key)
        logger.info(
            "s3_upload_identification",
            key=key,
            scientific_name=scientific_name,
            confidence=confidence_value,
        )
        return url

    async def download_and_rehost(
        self,
        external_url: str,
        scientific_name: str,
    ) -> str:
        image_bytes = await self._fetch_external(external_url)
        key = _build_reference_key(scientific_name)

        await self._put_object(
            key=key,
            body=image_bytes,
            content_type=_DEFAULT_CONTENT_TYPE,
        )

        url = self._public_url(key)
        logger.info(
            "s3_rehost_reference",
            key=key,
            scientific_name=scientific_name,
            source_url=external_url,
        )
        return url

    async def upload_training_image(self, image_bytes: bytes, scientific_name: str) -> str:
        key = _build_training_key(scientific_name)
        await self._put_object(key=key, body=image_bytes, content_type=_DEFAULT_CONTENT_TYPE)
        return key

    async def delete_user_images(self, user_id: UserId) -> int:
        deleted = 0
        try:
            async with self._session.client("s3") as s3:
                paginator = s3.get_paginator("list_objects_v2")
                # A page holds up to 1000 keys, the most `delete_objects` takes at once
                async for page in paginator.paginate(Bucket=self._bucket, Prefix=_user_prefix(user_id)):
                    keys = [obj["Key"] for obj in page.get("Contents", []) if "Key" in obj]
                    if keys:
                        await s3.delete_objects(
                            Bucket=self._bucket,
                            Delete={"Objects": [{"Key": key} for key in keys], "Quiet": True},
                        )
                        deleted += len(keys)
        except (BotoCoreError, ClientError) as exc:
            raise ExternalServiceError(message=type(exc).__name__, service="S3", retryable=True) from exc
        logger.info("s3_delete_user_images", user_id=str(user_id), deleted=deleted)
        return deleted

    async def _put_object(
        self,
        key: str,
        body: bytes,
        content_type: str,
    ) -> None:
        async with self._session.client("s3") as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                ACL="public-read",
            )

    async def _fetch_external(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def _public_url(self, key: str) -> str:
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"