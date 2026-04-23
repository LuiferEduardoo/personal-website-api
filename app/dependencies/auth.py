from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.security import decode_access_token
from app.dependencies.db import AsyncDBSession
from app.models.user import User
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer(auto_error=True)
optional_bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: AsyncDBSession,
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    sub = payload.get("sub")
    if sub is None:
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = int(sub)
    except (TypeError, ValueError) as exc:
        raise _CREDENTIALS_EXCEPTION from exc

    user = await UserRepository(session).get(user_id)
    if user is None or user.deleted_at is not None:
        raise _CREDENTIALS_EXCEPTION

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(optional_bearer_scheme)
    ],
    session: AsyncDBSession,
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        return None

    sub = payload.get("sub")
    if sub is None:
        return None

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None

    user = await UserRepository(session).get(user_id)
    if user is None or user.deleted_at is not None:
        return None
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]

# "Decorator" for protected endpoints. Usage:
#   @router.post("/foo", dependencies=protected)
# If the endpoint also needs the authenticated user, declare it as
# `current_user: CurrentUser`. FastAPI caches the dependency within a request
# so the token is verified only once even if both are used together.
protected: list = [Depends(get_current_user)]
