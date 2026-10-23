"""The storage backends: keys in, signed links out, and the local links only open what they signed."""
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest

from src.shared.adapters import LocalImageStorage, S3ImageStorage
from src.shared.domain import ImageNotFoundError, UserId

TTL = 3600
START = 1_800_000_000.0


class _Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> float:
        return self.now


def _local(root: Path, clock: _Clock | None = None) -> LocalImageStorage:
    return LocalImageStorage(
        root=str(root), public_url="https://api.plante.test/", secret_key="secret", link_ttl_seconds=TTL,
        clock=clock or _Clock(),
    )


def _link_parts(url: str) -> tuple[str, int, str]:
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    return parts.path.removeprefix("/images/"), int(query["exp"][0]), query["sig"][0]


async def test_local_link_opens_the_stored_photo(tmp_path: Path) -> None:
    # Arrange
    storage = _local(tmp_path)
    key = await storage.upload_identification_image(b"photo", "Monstera deliciosa", 0.9, UserId(uuid4()))

    # Act
    url = await storage.signed_url(key)
    path, remaining = storage.open_signed(*_link_parts(url))

    # Assert
    assert url.startswith(f"https://api.plante.test/images/{key}?")
    assert path.read_bytes() == b"photo"
    assert TTL <= remaining <= 2 * TTL


async def test_local_link_stays_the_same_within_a_lifetime_and_then_expires(tmp_path: Path) -> None:
    # Arrange
    clock = _Clock()
    storage = _local(tmp_path, clock)
    key = await storage.upload_training_image(b"photo", "Monstera deliciosa")
    first = await storage.signed_url(key)

    # Act
    clock.now += 60
    same = await storage.signed_url(key)
    clock.now += 2 * TTL

    # Assert: cacheable for a while, and then the old link no longer opens
    assert same == first
    with pytest.raises(ImageNotFoundError):
        storage.open_signed(*_link_parts(first))


@pytest.mark.parametrize("tamper", ["signature", "key", "deadline"])
async def test_local_link_does_not_open_when_tampered(tmp_path: Path, tamper: str) -> None:
    # Arrange
    storage = _local(tmp_path)
    user = UserId(uuid4())
    mine = await storage.upload_identification_image(b"mine", "Monstera deliciosa", 0.9, user)
    other = await storage.upload_identification_image(b"other", "Monstera deliciosa", 0.9, user)
    key, expires, signature = _link_parts(await storage.signed_url(mine))
    tampered = {
        "signature": (key, expires, "0" * len(signature)),
        "key": (other, expires, signature),
        "deadline": (key, expires + TTL, signature),
    }[tamper]

    # Act & Assert
    with pytest.raises(ImageNotFoundError):
        storage.open_signed(*tampered)


async def test_local_link_never_leaves_the_root(tmp_path: Path) -> None:
    # Arrange: a file next to the root, and a valid signature for a key that climbs to it
    root = tmp_path / "images"
    root.mkdir()
    (tmp_path / "secret.txt").write_text("secret")
    storage = _local(root)

    # Act & Assert
    with pytest.raises(ImageNotFoundError):
        storage.open_signed(*_link_parts(await storage.signed_url("../secret.txt")))


async def test_local_link_to_a_deleted_photo_is_not_found(tmp_path: Path) -> None:
    # Arrange
    storage = _local(tmp_path)
    user = UserId(uuid4())
    url = await storage.signed_url(await storage.upload_identification_image(b"photo", "Monstera deliciosa", 0.9, user))

    # Act
    await storage.delete_user_images(user)

    # Assert
    with pytest.raises(ImageNotFoundError):
        storage.open_signed(*_link_parts(url))


async def test_local_delete_takes_only_the_users_photos(tmp_path: Path) -> None:
    # Arrange
    storage = _local(tmp_path)
    user, other = UserId(uuid4()), UserId(uuid4())
    for _ in range(2):
        await storage.upload_identification_image(b"photo", "Monstera deliciosa", 0.9, user)
    others = await storage.upload_identification_image(b"photo", "Monstera deliciosa", 0.9, other)
    training = await storage.upload_training_image(b"photo", "Monstera deliciosa")

    # Act
    deleted = await storage.delete_user_images(user)

    # Assert
    assert deleted == 2
    assert (tmp_path / others).is_file() and (tmp_path / training).is_file()
    assert await storage.delete_user_images(user) == 0  # nothing left, no error


async def test_s3_link_is_presigned_for_the_configured_endpoint() -> None:
    # Arrange: R2 is S3 with another endpoint; signing needs no request to it
    storage = S3ImageStorage(
        bucket_name="plante", region="auto", aws_access_key_id="key", aws_secret_access_key="secret",
        link_ttl_seconds=600, endpoint_url="https://account.r2.cloudflarestorage.com",
    )

    # Act
    url = await storage.signed_url("identifications/a.jpg")

    # Assert
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    assert (parts.netloc, parts.path) == ("account.r2.cloudflarestorage.com", "/plante/identifications/a.jpg")
    assert query["X-Amz-Expires"] == ["600"] and "X-Amz-Signature" in query
