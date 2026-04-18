from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.dependencies.auth import CurrentUser, protected
from app.dependencies.db import AsyncDBSession
from app.dependencies.storage import ImageServiceDep
from app.repositories.user import UserRepository
from app.schemas.user import UserRead, UserUpdateMe
from app.services.image import InvalidImageUrlError
from app.services.image_converter import ImageConverterError
from app.services.storage import StorageUploadError
from app.services.user import EmailAlreadyRegisteredError, UserService

PROFILE_PHOTO_FOLDER = "users/profile"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(session: AsyncDBSession) -> UserService:
    return UserService(UserRepository(session))


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get the authenticated user with their profile photo",
    dependencies=protected,
)
async def get_me(current_user: CurrentUser, user_service: UserServiceDep) -> UserRead:
    user = await user_service.get_profile(current_user.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserRead.model_validate(user)


@router.patch(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update the authenticated user (name and email only)",
    dependencies=protected,
)
async def update_me(
    payload: UserUpdateMe,
    current_user: CurrentUser,
    user_service: UserServiceDep,
) -> UserRead:
    try:
        user = await user_service.update_profile(
            current_user, payload.model_dump(exclude_unset=True)
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserRead.model_validate(user)


@router.patch(
    "/me/profile-photo",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update the authenticated user's profile photo (file or URL)",
    dependencies=protected,
)
async def update_profile_photo(
    current_user: CurrentUser,
    user_service: UserServiceDep,
    image_service: ImageServiceDep,
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
) -> UserRead:
    if (file is None) == (url is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of 'file' or 'url'.",
        )

    try:
        if file is not None:
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
            image = await image_service.upload(data, folder=PROFILE_PHOTO_FOLDER)
        else:
            assert url is not None
            image = await image_service.upload_from_url(
                url, folder=PROFILE_PHOTO_FOLDER
            )
    except InvalidImageUrlError as exc:
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

    user = await user_service.set_profile_photo(current_user, image.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserRead.model_validate(user)
