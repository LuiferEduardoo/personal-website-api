from typing import Annotated

from fastapi import Depends

from app.core.config import settings
from app.core.storage import get_r2_client
from app.dependencies.db import AsyncDBSession
from app.repositories.image import ImageRepository
from app.services.image import ImageService
from app.services.image_converter import ImageConverterService
from app.services.storage import S3StorageService


def get_image_converter_service() -> ImageConverterService:
    return ImageConverterService()


def get_storage_service() -> S3StorageService:
    return S3StorageService(
        client=get_r2_client(),
        bucket=settings.r2_bucket_name,
        public_base_url=settings.r2_public_base_url,
    )


ImageConverterServiceDep = Annotated[
    ImageConverterService, Depends(get_image_converter_service)
]
StorageServiceDep = Annotated[S3StorageService, Depends(get_storage_service)]


def get_image_service(
    session: AsyncDBSession,
    converter: ImageConverterServiceDep,
    storage: StorageServiceDep,
) -> ImageService:
    return ImageService(ImageRepository(session), converter, storage)


ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]
