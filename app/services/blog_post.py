from collections.abc import Sequence

from app.core.text import estimate_reading_time, slugify
from app.models.blog_post import BlogPost
from app.models.image import Image
from app.models.user import User
from app.repositories.blog_post import BlogPostRepository
from app.repositories.category import CategoryRepository
from app.repositories.subcategory import SubcategoryRepository
from app.services.image import ImageService


class InvalidCategoriesError(Exception):
    """Raised when some of the supplied category IDs do not exist."""


class InvalidSubcategoriesError(Exception):
    """Raised when some of the supplied subcategory IDs do not exist."""


class BlogPostService:
    def __init__(
        self,
        blog_post_repository: BlogPostRepository,
        category_repository: CategoryRepository,
        subcategory_repository: SubcategoryRepository,
        image_service: ImageService,
    ) -> None:
        self.blog_post_repository = blog_post_repository
        self.category_repository = category_repository
        self.subcategory_repository = subcategory_repository
        self.image_service = image_service

    async def create(
        self,
        *,
        author: User,
        title: str,
        content: str,
        category_ids: Sequence[int],
        subcategory_ids: Sequence[int],
        image_file: bytes | None = None,
        image_url: str | None = None,
    ) -> BlogPost:
        categories = await self._fetch_categories(category_ids)
        subcategories = await self._fetch_subcategories(subcategory_ids)
        cover_image = await self._build_cover_image(image_file, image_url)

        post = BlogPost(
            title=title,
            content=content,
            link=slugify(title),
            user_id=author.id,
            cover_image_id=cover_image.id,
            reading_time=estimate_reading_time(content),
        )
        post.user = author
        post.cover_image = cover_image
        post.authors = [author]
        post.categories = list(categories)
        post.subcategories = list(subcategories)

        session = self.blog_post_repository.session
        session.add(post)
        await session.flush()
        await session.refresh(post, ["created_at", "updated_at"])
        await session.commit()
        return post

    async def _fetch_categories(self, ids: Sequence[int]):
        unique_ids = list(dict.fromkeys(ids))
        categories = await self.category_repository.list_by_ids(unique_ids)
        if len(categories) != len(unique_ids):
            raise InvalidCategoriesError(
                "One or more categories do not exist or are deleted."
            )
        return categories

    async def _fetch_subcategories(self, ids: Sequence[int]):
        unique_ids = list(dict.fromkeys(ids))
        subcategories = await self.subcategory_repository.list_by_ids(unique_ids)
        if len(subcategories) != len(unique_ids):
            raise InvalidSubcategoriesError(
                "One or more subcategories do not exist or are deleted."
            )
        return subcategories

    async def _build_cover_image(
        self, image_file: bytes | None, image_url: str | None
    ) -> Image:
        if image_file is not None:
            return await self.image_service.upload(image_file, folder="blog")
        assert image_url is not None
        return await self.image_service.upload_from_url(image_url, folder="blog")
