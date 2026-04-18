from datetime import timedelta

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.user import UserRepository


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def authenticate(self, email: str, password: str) -> User | None:
        user = await self.user_repository.get_by_email(email)
        if user is None:
            return None
        if not verify_password(password, user.password):
            return None
        return user

    def issue_access_token(self, user: User) -> tuple[str, int]:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        token = create_access_token(subject=user.id, expires_delta=expires_delta)
        return token, int(expires_delta.total_seconds())
