import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

from src.shared.domain.exceptions import InvalidImageError
from src.shared.domain.ports.image_sanitizer import IImageSanitizer

# HEIC (iPhone) opens as "HEIF"; pillow-heif applies its rotation on decode
register_heif_opener()
_SUPPORTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "HEIF"})
# Acima disso a imagem descomprimida ocupa centenas de MB (proteção contra "decompression bomb");
# fotos de celular ficam bem abaixo (48 MP ≈ 48 milhões de pixels)
_MAX_PIXELS = 60_000_000
_JPEG_QUALITY = 90


class PillowImageSanitizer(IImageSanitizer):
    """
    Regrava a imagem a partir dos pixels: a orientação do EXIF é aplicada antes e nenhum
    metadado é copiado para o arquivo novo. Aceita JPEG, PNG, WebP e HEIC (iPhone); a saída é
    sempre JPEG.
    """

    def sanitize(self, image_bytes: bytes) -> bytes:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(image_bytes)) as image:
                    if image.format not in _SUPPORTED_FORMATS:
                        raise InvalidImageError()
                    width, height = image.size
                    if width * height > _MAX_PIXELS:
                        raise InvalidImageError()
                    upright = ImageOps.exif_transpose(image)
                    pixels = upright.convert("RGB")
        except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError) as exc:
            raise InvalidImageError() from exc

        output = io.BytesIO()
        # Sem `exif=`/`icc_profile=`: o JPEG novo sai sem nenhum metadado
        pixels.save(output, format="JPEG", quality=_JPEG_QUALITY)
        return output.getvalue()
