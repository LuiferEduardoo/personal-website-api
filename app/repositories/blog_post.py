from sqlalchemy import select
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
