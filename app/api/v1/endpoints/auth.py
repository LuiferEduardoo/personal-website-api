from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies.auth import CurrentUser, protected
from app.dependencies.db import AsyncDBSession
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, PasswordChangeRequest, TokenResponse
from app.services.auth import AuthService, InvalidCurrentPasswordError

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: AsyncDBSession) -> AuthService:
    return AuthService(UserRepository(session))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user and return an access token",
)
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    user = await auth_service.authenticate(payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token, expires_in = auth_service.issue_access_token(user)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the authenticated user's password",
    dependencies=protected,
)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
) -> Response:
    try:
        await auth_service.change_password(
            current_user, payload.current_password, payload.new_password
        )
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
