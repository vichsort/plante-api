import asyncio
import hashlib
import hmac
import shutil
import time
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import structlog

from src.shared.adapters.storage.keys import (
    fetch_external,
    identification_key,
    reference_key,
    training_key,
    user_prefix,
)
from src.shared.domain.exceptions import ExternalServiceError, ImageNotFoundError
from src.shared.domain.ports.image_storage import IImageStorage
from src.shared.domain.value_objects.ids import UserId

logger = structlog.stdlib.get_logger()

# The links are signed with a key derived from the app secret, never with the secret itself
_LINK_KEY_LABEL = b"plante:image-links"
IMAGES_PATH = "/images"


class LocalImageStorage(IImageStorage):
    """
    Images in a folder on the server's disk, served by the API itself (`IMAGES_PATH`) through
    links signed with HMAC. Backing up the folder is the server's job: the training dataset lives
    there too.
    """

    def __init__(
        self,
        root: str,
        public_url: str,
        secret_key: str,
        link_ttl_seconds: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._root = Path(root).resolve()
        self._public_url = public_url.rstrip("/")
        self._link_key = hmac.new(secret_key.encode(), _LINK_KEY_LABEL, hashlib.sha256).digest()
        self._link_ttl_seconds = link_ttl_seconds
        self._clock = clock

    async def upload_identification_image(
        self,
        image_bytes: bytes,
        scientific_name: str,
        confidence_value: float,
        user_id: UserId,
    ) -> str:
        key = identification_key(user_id, scientific_name)
        await self._write(key, image_bytes)
        logger.info(
            "local_upload_identification",
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
        await self._write(key, image_bytes)
        logger.info(
            "local_rehost_reference",
            key=key,
            scientific_name=scientific_name,
            source_url=external_url,
        )
        return key

    async def upload_training_image(self, image_bytes: bytes, scientific_name: str) -> str:
        key = training_key(scientific_name)
        await self._write(key, image_bytes)
        return key

    async def delete_user_images(self, user_id: UserId) -> int:
        folder = self._path(user_prefix(user_id))
        try:
            deleted = await asyncio.to_thread(_delete_tree, folder)
        except OSError as exc:
            raise ExternalServiceError(message=type(exc).__name__, service="Disk", retryable=True) from exc
        logger.info("local_delete_user_images", user_id=str(user_id), deleted=deleted)
        return deleted

    async def signed_url(self, key: str) -> str:
        # The deadline moves in steps of one lifetime, so the link of a photo stays the same for a
        # while and the browser can cache it; it lasts between one and two lifetimes
        step = self._link_ttl_seconds
        expires = (int(self._clock()) // step + 2) * step
        return f"{self._public_url}{IMAGES_PATH}/{quote(key)}?exp={expires}&sig={self._sign(key, expires)}"

    def open_signed(self, key: str, expires: int, signature: str) -> tuple[Path, int]:
        """
        The file behind a link and how many seconds the link has left. Raises `ImageNotFoundError`
        when the signature does not match, the link expired or the file is gone, without saying
        which (a guess learns nothing).
        """
        remaining = expires - int(self._clock())
        if remaining <= 0 or not hmac.compare_digest(signature, self._sign(key, expires)):
            raise ImageNotFoundError()
        path = self._path(key)
        if not path.is_file():
            raise ImageNotFoundError()
        return path, remaining

    def _sign(self, key: str, expires: int) -> str:
        return hmac.new(self._link_key, f"{key}\n{expires}".encode(), hashlib.sha256).hexdigest()

    def _path(self, key: str) -> Path:
        # Keys come from us, but a path never leaves the root, even with a valid signature
        relative = PurePosixPath(key)
        if relative.is_absolute() or ".." in relative.parts or "\\" in key:
            raise ImageNotFoundError()
        path = (self._root / relative).resolve()
        if not path.is_relative_to(self._root):
            raise ImageNotFoundError()
        return path

    async def _write(self, key: str, body: bytes) -> None:
        await asyncio.to_thread(_write_file, self._path(key), body)


def _write_file(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def _delete_tree(folder: Path) -> int:
    if not folder.is_dir():
        return 0
    count = sum(1 for item in folder.rglob("*") if item.is_file())
    shutil.rmtree(folder)
    return count
