from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_post import BlogPost
from app.repositories.base import BaseRepository


class BlogPostRepository(BaseRepository[BlogPost]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BlogPost, session)

    async def get_active(self, post_id: int) -> BlogPost | None:
        stmt = select(BlogPost).where(
            BlogPost.id == post_id,
            BlogPost.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_visible(
        self, limit: int, offset: int, *, include_hidden: bool = False
    ) -> list[BlogPost]:
        stmt = select(BlogPost).where(BlogPost.deleted_at.is_(None))
        if not include_hidden:
            stmt = stmt.where(BlogPost.visible.is_(True))
        stmt = (
            stmt.order_by(BlogPost.created_at.desc(), BlogPost.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_visible(self, *, include_hidden: bool = False) -> int:
        stmt = select(func.count()).select_from(BlogPost).where(
            BlogPost.deleted_at.is_(None)
        )
        if not include_hidden:
            stmt = stmt.where(BlogPost.visible.is_(True))
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_visible(
        self, post_id: int, *, include_hidden: bool = False
    ) -> BlogPost | None:
        stmt = select(BlogPost).where(
            BlogPost.id == post_id,
            BlogPost.deleted_at.is_(None),
        )
        if not include_hidden:
            stmt = stmt.where(BlogPost.visible.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_visible_by_link(
        self, link: str, *, include_hidden: bool = False
    ) -> BlogPost | None:
        stmt = select(BlogPost).where(
            BlogPost.link == link,
            BlogPost.deleted_at.is_(None),
        )
        if not include_hidden:
            stmt = stmt.where(BlogPost.visible.is_(True))
        stmt = stmt.order_by(BlogPost.created_at.desc(), BlogPost.id.desc())
        result = await self.session.execute(stmt)
        return result.scalars().first()
