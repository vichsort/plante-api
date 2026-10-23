"""The `/images` route serves the local storage's links and nothing else."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.adapters import LocalImageStorage
from src.shared.api import (
    images_router,
    install_image_links,
    register_exception_handlers,
)
from src.shared.domain import IImageStorage
from src.shared.tests.fakes import RecordingImageStorage


def _client(storage: IImageStorage) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    install_image_links(app, lambda: storage)
    app.include_router(images_router)
    return TestClient(app)


def _local(root: Path) -> LocalImageStorage:
    return LocalImageStorage(root=str(root), public_url="http://testserver", secret_key="secret", link_ttl_seconds=3600)


async def test_a_signed_link_serves_the_photo(tmp_path: Path) -> None:
    # Arrange
    storage = _local(tmp_path)
    url = await storage.signed_url(await storage.upload_training_image(b"photo", "Monstera deliciosa"))

    # Act
    response = _client(storage).get(url)

    # Assert
    assert response.status_code == 200
    assert (response.content, response.headers["content-type"]) == (b"photo", "image/jpeg")
    assert response.headers["cache-control"].startswith("private, max-age=")


async def test_a_bad_signature_is_not_found(tmp_path: Path) -> None:
    # Arrange
    storage = _local(tmp_path)
    url = await storage.signed_url(await storage.upload_training_image(b"photo", "Monstera deliciosa"))

    # Act
    response = _client(storage).get(url.replace("sig=", "sig=0"))

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (404, "PLANTE_4032_IMAGE_NOT_FOUND")


def test_without_the_local_storage_the_route_is_not_found() -> None:
    # Act
    response = _client(RecordingImageStorage()).get("/images/identifications/a.jpg?exp=1&sig=x")

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (404, "PLANTE_4032_IMAGE_NOT_FOUND")
