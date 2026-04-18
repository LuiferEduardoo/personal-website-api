from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.image import Image
from app.repositories.base import BaseRepository


class ImageRepository(BaseRepository[Image]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Image, session)

    async def get_active(self, image_id: int) -> Image | None:
        stmt = select(Image).where(
            Image.id == image_id,
            Image.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
