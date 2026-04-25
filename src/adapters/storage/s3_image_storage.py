import base64
import uuid
from io import BytesIO
import aioboto3
import httpx
from structlog import get_logger

from src.domain.ports.image_storage import IImageStorage

logger = get_logger()

_IDENTIFICATION_PREFIX = "identifications"
_REFERENCES_PREFIX = "species/references"
_DEFAULT_CONTENT_TYPE = "image/jpeg"

def _sanitize(scientific_name: str) -> str:
    """Converte 'Monstera deliciosa' → 'monstera_deliciosa' para uso em chaves S3."""
    return scientific_name.lower().replace(" ", "_")

def _build_identification_key(scientific_name: str) -> str:
    return f"{_IDENTIFICATION_PREFIX}/{_sanitize(scientific_name)}/{uuid.uuid4()}.jpg"

def _build_reference_key(scientific_name: str) -> str:
    return f"{_REFERENCES_PREFIX}/{_sanitize(scientific_name)}/{uuid.uuid4()}.jpg"

class S3ImageStorage(IImageStorage):
    """
    Adapter de saída — armazenamento de imagens no S3.

    Bucket público (sem CloudFront). Objetos são gravados com
    ACL public-read, portanto a URL permanente é:
        https://{bucket}.s3.{region}.amazonaws.com/{key}

    Variáveis de ambiente necessárias (via Settings):
        S3_BUCKET_NAME
        S3_REGION
        AWS_ACCESS_KEY_ID
        AWS_SECRET_ACCESS_KEY
    """

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
        image_b64: str,
        scientific_name: str,
        confidence_value: float,
        user_id: int,
    ) -> str:
        """
        Faz upload de uma imagem base64 para o bucket.
        Retorna a URL pública permanente do objeto.
        """
        image_bytes = base64.b64decode(image_b64)
        key = _build_identification_key(scientific_name)

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
        """
        Baixa uma imagem de URL externa (ex: Kindwise) e re-hospeda no bucket
        no prefixo species/references/{scientific_name}/.
        Retorna a URL pública permanente do objeto.
        """
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