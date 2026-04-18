from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog_post import BlogPost
from app.repositories.base import BaseRepository


class BlogPostRepository(BaseRepository[BlogPost]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BlogPost, session)
