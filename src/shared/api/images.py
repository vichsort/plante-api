"""
The route behind the links of the local storage. Anyone holding a valid link sees the image (an
`<img>` cannot send a token); without the local storage the route answers 404.
"""
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Query, Request
from fastapi.responses import FileResponse

from src.shared.adapters.storage.keys import CONTENT_TYPE
from src.shared.adapters.storage.local import IMAGES_PATH, LocalImageStorage
from src.shared.api.openapi import error_responses
from src.shared.domain import IImageStorage, ImageNotFoundError

_STATE_KEY = "image_storage"

router = APIRouter(prefix=IMAGES_PATH, tags=["images"])


def install_image_links(app: FastAPI, storage: Callable[[], IImageStorage]) -> None:
    """Receives the factory (the container provider), so an override in the container holds here too."""
    setattr(app.state, _STATE_KEY, storage)


def _local_storage(request: Request) -> LocalImageStorage:
    factory = getattr(request.app.state, _STATE_KEY, None)
    storage = factory() if callable(factory) else None
    if not isinstance(storage, LocalImageStorage):
        raise ImageNotFoundError()
    return storage


@router.get(
    "/{key:path}",
    response_class=FileResponse,
    responses={200: {"content": {CONTENT_TYPE: {}}}, **error_responses(ImageNotFoundError)},
)
def get_image(
    key: str,
    exp: Annotated[int, Query(description="Link deadline (Unix time).")],
    sig: Annotated[str, Query(description="Link signature.")],
    storage: Annotated[LocalImageStorage, Depends(_local_storage)],
) -> FileResponse:
    """An image from a signed link (`image_url` and `primary_image_url` in the other responses)."""
    path, remaining = storage.open_signed(key, exp, sig)
    return FileResponse(path, media_type=CONTENT_TYPE, headers={"Cache-Control": f"private, max-age={remaining}"})
