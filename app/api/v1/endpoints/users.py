from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import CurrentUser, protected
from app.dependencies.db import AsyncDBSession
from app.repositories.user import UserRepository
from app.schemas.user import UserRead
from app.services.user import UserService

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
