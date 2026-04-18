from app.models.user import User
from app.repositories.user import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def get_profile(self, user_id: int) -> User | None:
        return await self.user_repository.get_with_profile_photo(user_id)
