from collections.abc import Sequence
from datetime import datetime, timezone

from app.core.text import estimate_reading_time, slugify
from app.models.blog_post import BlogPost
from app.models.image import Image
from app.models.user import User
from app.repositories.blog_post import BlogPostRepository
from app.repositories.category import CategoryRepository
from app.repositories.subcategory import SubcategoryRepository
from app.services.image import ImageService
from app.services.taxonomy import fetch_categories, fetch_subcategories


class BlogPostNotFoundError(Exception):
    """Raised when a blog post cannot be found or is soft-deleted."""


class BlogPostForbiddenError(Exception):
    """Raised when a user tries to modify a blog post they do not own."""


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
        categories = await fetch_categories(self.category_repository, category_ids)
        subcategories = await fetch_subcategories(
            self.subcategory_repository, subcategory_ids
        )
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

    async def update(
        self,
        *,
        post_id: int,
        requester: User,
        title: str | None = None,
        content: str | None = None,
        visible: bool | None = None,
        category_ids: Sequence[int] | None = None,
        subcategory_ids: Sequence[int] | None = None,
        image_file: bytes | None = None,
        image_url: str | None = None,
    ) -> BlogPost:
        post = await self.blog_post_repository.get_active(post_id)
        if post is None:
            raise BlogPostNotFoundError()
        if post.user_id != requester.id:
            raise BlogPostForbiddenError()

        if category_ids is not None:
            categories = await fetch_categories(self.category_repository, category_ids)
            post.categories = list(categories)
        if subcategory_ids is not None:
            subcategories = await fetch_subcategories(
                self.subcategory_repository, subcategory_ids
            )
            post.subcategories = list(subcategories)

        if title is not None:
            post.title = title
            post.link = slugify(title)
        if content is not None:
            post.content = content
            post.reading_time = estimate_reading_time(content)
        if visible is not None:
            post.visible = visible

        if image_file is not None or image_url is not None:
            cover_image = await self._build_cover_image(image_file, image_url)
            post.cover_image = cover_image
            post.cover_image_id = cover_image.id

        session = self.blog_post_repository.session
        await session.flush()
        await session.refresh(post, ["updated_at"])
        await session.commit()
        return post

    async def list_visible(
        self, *, limit: int, offset: int, include_hidden: bool = False
    ) -> tuple[list[BlogPost], int]:
        items = await self.blog_post_repository.list_visible(
            limit, offset, include_hidden=include_hidden
        )
        total = await self.blog_post_repository.count_visible(
            include_hidden=include_hidden
        )
        return items, total

    async def get_visible(
        self, post_id: int, *, include_hidden: bool = False
    ) -> BlogPost:
        post = await self.blog_post_repository.get_visible(
            post_id, include_hidden=include_hidden
        )
        if post is None:
            raise BlogPostNotFoundError()
        return post

    async def get_visible_by_link(
        self, link: str, *, include_hidden: bool = False
    ) -> BlogPost:
        post = await self.blog_post_repository.get_visible_by_link(
            link, include_hidden=include_hidden
        )
        if post is None:
            raise BlogPostNotFoundError()
        return post

    async def delete(self, *, post_id: int, requester: User) -> None:
        post = await self.blog_post_repository.get_active(post_id)
        if post is None:
            raise BlogPostNotFoundError()
        if post.user_id != requester.id:
            raise BlogPostForbiddenError()

        post.deleted_at = datetime.now(timezone.utc)
        await self.blog_post_repository.session.commit()

    async def _build_cover_image(
        self, image_file: bytes | None, image_url: str | None
    ) -> Image:
        if image_file is not None:
            return await self.image_service.upload(image_file, folder="blog")
        assert image_url is not None
        return await self.image_service.upload_from_url(image_url, folder="blog")
