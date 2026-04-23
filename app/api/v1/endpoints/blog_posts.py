from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)

from app.dependencies.auth import CurrentUser, OptionalUser, protected
from app.dependencies.db import AsyncDBSession
from app.dependencies.storage import ImageServiceDep
from app.repositories.blog_post import BlogPostRepository
from app.repositories.category import CategoryRepository
from app.repositories.subcategory import SubcategoryRepository
from app.schemas.blog_post import BlogPostRead, PaginatedBlogPosts
from app.services.blog_post import (
    BlogPostForbiddenError,
    BlogPostNotFoundError,
    BlogPostService,
)
from app.services.image import InvalidImageUrlError
from app.services.image_converter import ImageConverterError
from app.services.storage import StorageUploadError
from app.services.taxonomy import InvalidCategoriesError, InvalidSubcategoriesError

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


@router.get(
    "",
    response_model=PaginatedBlogPosts,
    status_code=status.HTTP_200_OK,
    summary="List visible blog posts (paginated)",
)
async def list_blog_posts(
    blog_post_service: BlogPostServiceDep,
    current_user: OptionalUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedBlogPosts:
    items, total = await blog_post_service.list_visible(
        limit=limit, offset=offset, include_hidden=current_user is not None
    )
    return PaginatedBlogPosts(
        items=[BlogPostRead.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/link/{link}",
    response_model=BlogPostRead,
    status_code=status.HTTP_200_OK,
    summary="Get a visible blog post by its link (slug)",
)
async def get_blog_post_by_link(
    link: str,
    blog_post_service: BlogPostServiceDep,
    current_user: OptionalUser,
) -> BlogPostRead:
    try:
        post = await blog_post_service.get_visible_by_link(
            link, include_hidden=current_user is not None
        )
    except BlogPostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found"
        ) from exc
    return BlogPostRead.model_validate(post)


@router.get(
    "/{post_id}",
    response_model=BlogPostRead,
    status_code=status.HTTP_200_OK,
    summary="Get a visible blog post by id",
)
async def get_blog_post(
    post_id: int,
    blog_post_service: BlogPostServiceDep,
    current_user: OptionalUser,
) -> BlogPostRead:
    try:
        post = await blog_post_service.get_visible(
            post_id, include_hidden=current_user is not None
        )
    except BlogPostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found"
        ) from exc
    return BlogPostRead.model_validate(post)


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


@router.patch(
    "/{post_id}",
    response_model=BlogPostRead,
    status_code=status.HTTP_200_OK,
    summary="Update a blog post (only the owner; cover image optional via file or URL)",
    dependencies=protected,
)
async def update_blog_post(
    post_id: int,
    current_user: CurrentUser,
    blog_post_service: BlogPostServiceDep,
    title: Annotated[str | None, Form(min_length=1, max_length=512)] = None,
    content: Annotated[str | None, Form(min_length=1)] = None,
    visible: Annotated[bool | None, Form()] = None,
    category_ids: Annotated[list[int] | None, Form()] = None,
    subcategory_ids: Annotated[list[int] | None, Form()] = None,
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
) -> BlogPostRead:
    if file is not None and url is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at most one of 'file' or 'url'.",
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
        post = await blog_post_service.update(
            post_id=post_id,
            requester=current_user,
            title=title,
            content=content,
            visible=visible,
            category_ids=category_ids,
            subcategory_ids=subcategory_ids,
            image_file=image_bytes,
            image_url=url,
        )
    except BlogPostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found"
        ) from exc
    except BlogPostForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to edit this blog post",
        ) from exc
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


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a blog post (only the owner)",
    dependencies=protected,
)
async def delete_blog_post(
    post_id: int,
    current_user: CurrentUser,
    blog_post_service: BlogPostServiceDep,
) -> Response:
    try:
        await blog_post_service.delete(post_id=post_id, requester=current_user)
    except BlogPostNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found"
        ) from exc
    except BlogPostForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to delete this blog post",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
