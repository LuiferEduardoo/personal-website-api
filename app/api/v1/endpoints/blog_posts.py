from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.dependencies.auth import CurrentUser, protected
from app.dependencies.db import AsyncDBSession
from app.dependencies.storage import ImageServiceDep
from app.repositories.blog_post import BlogPostRepository
from app.repositories.category import CategoryRepository
from app.repositories.subcategory import SubcategoryRepository
from app.schemas.blog_post import BlogPostRead
from app.services.blog_post import (
    BlogPostService,
    InvalidCategoriesError,
    InvalidSubcategoriesError,
)
from app.services.image import InvalidImageUrlError
from app.services.image_converter import ImageConverterError
from app.services.storage import StorageUploadError

router = APIRouter(prefix="/blog-posts", tags=["blog-posts"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def get_blog_post_service(
    session: AsyncDBSession,
    image_service: ImageServiceDep,
) -> BlogPostService:
    return BlogPostService(
        blog_post_repository=BlogPostRepository(session),
        category_repository=CategoryRepository(session),
        subcategory_repository=SubcategoryRepository(session),
        image_service=image_service,
    )


BlogPostServiceDep = Annotated[BlogPostService, Depends(get_blog_post_service)]


@router.post(
    "",
    response_model=BlogPostRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a blog post (cover image via file or URL)",
    dependencies=protected,
)
async def create_blog_post(
    current_user: CurrentUser,
    blog_post_service: BlogPostServiceDep,
    title: Annotated[str, Form(min_length=1, max_length=512)],
    content: Annotated[str, Form(min_length=1)],
    category_ids: Annotated[list[int], Form(default_factory=list)],
    subcategory_ids: Annotated[list[int], Form(default_factory=list)],
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
) -> BlogPostRead:
    if (file is None) == (url is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of 'file' or 'url'.",
        )

    image_bytes: bytes | None = None
    if file is not None:
        if file.content_type is None or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File must be an image",
            )
        image_bytes = await file.read()
        if len(image_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
            )

    try:
        post = await blog_post_service.create(
            author=current_user,
            title=title,
            content=content,
            category_ids=category_ids,
            subcategory_ids=subcategory_ids,
            image_file=image_bytes,
            image_url=url,
        )
    except InvalidCategoriesError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except InvalidSubcategoriesError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except InvalidImageUrlError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except ImageConverterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unsupported image file",
        ) from exc
    except StorageUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload to storage",
        ) from exc

    return BlogPostRead.model_validate(post)
