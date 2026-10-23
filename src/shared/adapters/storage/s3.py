import aioboto3
import structlog
from botocore.exceptions import BotoCoreError, ClientError

from src.shared.adapters.storage.keys import (
    CONTENT_TYPE,
    fetch_external,
    identification_key,
    reference_key,
    training_key,
    user_prefix,
)
from src.shared.domain.exceptions import ExternalServiceError
from src.shared.domain.ports.image_storage import IImageStorage
from src.shared.domain.value_objects.ids import UserId

logger = structlog.stdlib.get_logger()


class S3ImageStorage(IImageStorage):
    """
    Any S3-compatible storage: AWS by default, Cloudflare R2 (or another) with `endpoint_url`.
    Objects are private; the client gets presigned links.
    """

    def __init__(
        self,
        bucket_name: str,
        region: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        link_ttl_seconds: int,
        endpoint_url: str | None = None,
    ) -> None:
        self._bucket = bucket_name
        self._endpoint_url = endpoint_url or None
        self._link_ttl_seconds = link_ttl_seconds
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
        key = identification_key(user_id, scientific_name)
        await self._put_object(key=key, body=image_bytes)
        logger.info(
            "s3_upload_identification",
            key=key,
            scientific_name=scientific_name,
            confidence=confidence_value,
        )
        return key

    async def download_and_rehost(
        self,
        external_url: str,
        scientific_name: str,
    ) -> str:
        image_bytes = await fetch_external(external_url)
        key = reference_key(scientific_name)
        await self._put_object(key=key, body=image_bytes)
        logger.info(
            "s3_rehost_reference",
            key=key,
            scientific_name=scientific_name,
            source_url=external_url,
        )
        return key

    async def upload_training_image(self, image_bytes: bytes, scientific_name: str) -> str:
        key = training_key(scientific_name)
        await self._put_object(key=key, body=image_bytes)
        return key

    async def delete_user_images(self, user_id: UserId) -> int:
        deleted = 0
        try:
            async with self._session.client("s3", endpoint_url=self._endpoint_url) as s3:
                paginator = s3.get_paginator("list_objects_v2")
                # A page holds up to 1000 keys, the most `delete_objects` takes at once
                async for page in paginator.paginate(Bucket=self._bucket, Prefix=user_prefix(user_id)):
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

    async def signed_url(self, key: str) -> str:
        # Signing is local (no request to the storage): it only fails on bad configuration
        async with self._session.client("s3", endpoint_url=self._endpoint_url) as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=self._link_ttl_seconds,
            )

    async def _put_object(self, key: str, body: bytes) -> None:
        async with self._session.client("s3", endpoint_url=self._endpoint_url) as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType=CONTENT_TYPE,
            )
