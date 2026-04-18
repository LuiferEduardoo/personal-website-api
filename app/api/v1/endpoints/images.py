from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from app.dependencies.auth import protected
from app.dependencies.storage import ImageServiceDep
from app.schemas.image import ImageRead
from app.services.image import ImageNotFoundError, InvalidFolderError
from app.services.image_converter import ImageConverterError
from app.services.storage import StorageUploadError

router = APIRouter(prefix="/images", tags=["images"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post(
    "",
    response_model=ImageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image (converted to WebP) to object storage",
    dependencies=protected,
)
async def upload_image(
    image_service: ImageServiceDep,
    file: UploadFile = File(...),
    folder: str | None = Form(default=None),
) -> ImageRead:
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File must be an image",
        )

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )

    try:
        image = await image_service.upload(data, folder=folder)
    except InvalidFolderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ImageConverterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unsupported image file",
        ) from exc
    except StorageUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload to storage",
        ) from exc

    return ImageRead.model_validate(image)


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete an image and remove it from object storage",
    dependencies=protected,
)
async def delete_image(image_id: int, image_service: ImageServiceDep) -> Response:
    try:
        await image_service.delete(image_id)
    except ImageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        ) from exc
    except StorageUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to delete from storage",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
