from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def get_active(self, project_id: int) -> Project | None:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_visible(
        self, limit: int, offset: int, *, include_hidden: bool = False
    ) -> list[Project]:
        stmt = select(Project).where(Project.deleted_at.is_(None))
        if not include_hidden:
            stmt = stmt.where(Project.visible.is_(True))
        stmt = (
            stmt.order_by(Project.created_at.desc(), Project.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_visible(self, *, include_hidden: bool = False) -> int:
        stmt = select(func.count()).select_from(Project).where(
            Project.deleted_at.is_(None)
        )
        if not include_hidden:
            stmt = stmt.where(Project.visible.is_(True))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_visible(
        self, project_id: int, *, include_hidden: bool = False
    ) -> Project | None:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.deleted_at.is_(None),
        )
        if not include_hidden:
            stmt = stmt.where(Project.visible.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_visible_by_link(
        self, link: str, *, include_hidden: bool = False
    ) -> Project | None:
        stmt = select(Project).where(
            Project.link == link,
            Project.deleted_at.is_(None),
        )
        if not include_hidden:
            stmt = stmt.where(Project.visible.is_(True))
        stmt = stmt.order_by(Project.created_at.desc(), Project.id.desc())
        result = await self.session.execute(stmt)
        return result.scalars().first()
