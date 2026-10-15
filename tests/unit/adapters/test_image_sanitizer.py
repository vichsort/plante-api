import io

import pytest
from PIL import Image

from src.adapters.images.pillow_image_sanitizer import PillowImageSanitizer
from src.domain.exceptions import InvalidImageError

_GPS_IFD = 0x8825
_ORIENTATION = 0x0112
_CAMERA_MAKE = 0x010F


def _photo_with_exif(orientation: int = 1) -> bytes:
    """JPEG 40x20 (paisagem) com GPS, fabricante e orientação no EXIF, como uma foto de celular."""
    image = Image.new("RGB", (40, 20), color=(30, 120, 40))
    exif = Image.Exif()
    exif[_CAMERA_MAKE] = "PhoneMaker"
    exif[_ORIENTATION] = orientation
    exif[_GPS_IFD] = {1: "S", 2: (23.0, 33.0, 1.0), 3: "W", 4: (46.0, 38.0, 2.0)}
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


def _encode(fmt: str, size: tuple[int, int] = (10, 10), mode: str = "RGB") -> bytes:
    output = io.BytesIO()
    Image.new(mode, size).save(output, format=fmt)
    return output.getvalue()


def test_fixture_photo_really_has_gps() -> None:
    with Image.open(io.BytesIO(_photo_with_exif())) as image:
        assert image.getexif().get_ifd(_GPS_IFD)


def test_removes_all_metadata() -> None:
    cleaned = PillowImageSanitizer().sanitize(_photo_with_exif())

    with Image.open(io.BytesIO(cleaned)) as image:
        assert image.format == "JPEG"
        assert len(image.getexif()) == 0
        assert "exif" not in image.info
        assert "icc_profile" not in image.info


def test_applies_orientation_before_removing_it() -> None:
    # Orientação 6 = girar 90°: a foto 40x20 deve sair em pé (20x40)
    cleaned = PillowImageSanitizer().sanitize(_photo_with_exif(orientation=6))

    with Image.open(io.BytesIO(cleaned)) as image:
        assert image.size == (20, 40)


@pytest.mark.parametrize(("fmt", "mode"), [("PNG", "RGBA"), ("WEBP", "RGB"), ("JPEG", "L")])
def test_supported_formats_become_rgb_jpeg(fmt: str, mode: str) -> None:
    cleaned = PillowImageSanitizer().sanitize(_encode(fmt, mode=mode))

    with Image.open(io.BytesIO(cleaned)) as image:
        assert (image.format, image.mode) == ("JPEG", "RGB")


@pytest.mark.parametrize("payload", [b"not an image", b"", _encode("GIF", mode="P"), _encode("BMP")])
def test_rejects_unsupported_or_unreadable_files(payload: bytes) -> None:
    with pytest.raises(InvalidImageError):
        PillowImageSanitizer().sanitize(payload)


def test_rejects_images_too_large_to_decode() -> None:
    # 8000x8000 = 64 MP; em PNG de 1 bit o arquivo é pequeno, mas descomprimido não
    with pytest.raises(InvalidImageError):
        PillowImageSanitizer().sanitize(_encode("PNG", size=(8000, 8000), mode="1"))
