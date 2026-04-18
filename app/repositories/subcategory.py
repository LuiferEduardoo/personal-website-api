from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subcategory import Subcategory
from app.repositories.base import BaseRepository


class SubcategoryRepository(BaseRepository[Subcategory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Subcategory, session)

    async def list_by_ids(self, ids: Sequence[int]) -> list[Subcategory]:
        if not ids:
            return []
        stmt = select(Subcategory).where(
            Subcategory.id.in_(ids),
            Subcategory.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
