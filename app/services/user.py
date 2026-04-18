from typing import Any

from app.models.user import User
from app.repositories.user import UserRepository


class EmailAlreadyRegisteredError(Exception):
    """Raised when an email is already registered by another user."""


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def get_profile(self, user_id: int) -> User | None:
        return await self.user_repository.get_with_profile_photo(user_id)

    async def update_profile(self, user: User, data: dict[str, Any]) -> User | None:
        new_email = data.get("email")
        if new_email is not None and new_email != user.email:
            existing = await self.user_repository.get_by_email(new_email)
            if existing is not None and existing.id != user.id:
                raise EmailAlreadyRegisteredError()

        for key, value in data.items():
            setattr(user, key, value)

        if data:
            await self.user_repository.session.commit()

        return await self.user_repository.get_with_profile_photo(user.id)
