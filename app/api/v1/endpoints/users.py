from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import CurrentUser, protected
from app.dependencies.db import AsyncDBSession
from app.repositories.user import UserRepository
from app.schemas.user import UserRead, UserUpdateMe
from app.services.user import EmailAlreadyRegisteredError, UserService

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
