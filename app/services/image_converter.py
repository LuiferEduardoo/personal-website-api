from io import BytesIO

from PIL import Image, UnidentifiedImageError


class ImageConverterError(Exception):
    """Raised when the input cannot be decoded or converted."""


class ImageConverterService:
    """Converts raw image bytes to WebP."""

    def to_webp(
        self,
        data: bytes,
        *,
        quality: int = 85,
        lossless: bool = False,
    ) -> bytes:
        try:
            with Image.open(BytesIO(data)) as img:
                img.load()
                buffer = BytesIO()
                img.save(
                    buffer,
                    format="WEBP",
                    quality=quality,
                    lossless=lossless,
                    method=6,
                )
                return buffer.getvalue()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ImageConverterError("Invalid image file") from exc
