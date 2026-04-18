import re
from datetime import datetime, timezone
from uuid import uuid4

from app.models.image import Image
from app.repositories.image import ImageRepository
from app.services.image_converter import ImageConverterService
from app.services.storage import S3StorageService

_ROOT_FOLDER = "img"
_FOLDER_PATTERN = re.compile(r"^[a-zA-Z0-9_\-/]{1,128}$")


class ImageNotFoundError(Exception):
    """Raised when an image cannot be found or is already deleted."""


class InvalidFolderError(Exception):
    """Raised when the supplied folder name contains unsafe characters."""


class ImageService:
    def __init__(
        self,
        image_repository: ImageRepository,
        converter: ImageConverterService,
        storage: S3StorageService,
    ) -> None:
        self.image_repository = image_repository
        self.converter = converter
        self.storage = storage

    async def upload(self, raw_data: bytes, folder: str | None = None) -> Image:
        full_folder = self._build_folder(folder)
        webp_bytes = self.converter.to_webp(raw_data)
        name = f"{uuid4().hex}.webp"
        key = f"{full_folder}/{name}"

        url = await self.storage.upload(
            webp_bytes, key=key, content_type="image/webp"
        )

        image = await self.image_repository.create(
            {"name": name, "folder": full_folder, "url": url}
        )
        await self.image_repository.session.commit()
        return image

    async def delete(self, image_id: int) -> None:
        image = await self.image_repository.get_active(image_id)
        if image is None:
            raise ImageNotFoundError()

        key = f"{image.folder}/{image.name}" if image.folder else image.name
        await self.storage.delete(key)

        now = datetime.now(timezone.utc)
        image.removed_at = now
        image.deleted_at = now
        await self.image_repository.session.commit()

    @staticmethod
    def _build_folder(folder: str | None) -> str:
        if folder is None:
            return _ROOT_FOLDER
        folder = folder.strip().strip("/")
        if not folder:
            return _ROOT_FOLDER
        if not _FOLDER_PATTERN.match(folder):
            raise InvalidFolderError(
                "Folder may only contain letters, digits, '-', '_' and '/'."
            )
        return f"{_ROOT_FOLDER}/{folder}"
