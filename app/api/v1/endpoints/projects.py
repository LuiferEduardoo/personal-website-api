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

from app.dependencies.auth import OptionalUser, protected
from app.dependencies.db import AsyncDBSession
from app.dependencies.storage import ImageServiceDep
from app.repositories.category import CategoryRepository
from app.repositories.project import ProjectRepository
from app.repositories.subcategory import SubcategoryRepository
from app.schemas.project import PaginatedProjects, ProjectRead
from app.services.image import InvalidImageUrlError
from app.services.image_converter import ImageConverterError
from app.services.project import ProjectNotFoundError, ProjectService
from app.services.storage import StorageUploadError
from app.services.taxonomy import InvalidCategoriesError, InvalidSubcategoriesError

router = APIRouter(prefix="/projects", tags=["projects"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def get_project_service(
    session: AsyncDBSession,
    image_service: ImageServiceDep,
) -> ProjectService:
    return ProjectService(
        project_repository=ProjectRepository(session),
        category_repository=CategoryRepository(session),
        subcategory_repository=SubcategoryRepository(session),
        image_service=image_service,
    )


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


@router.get(
    "",
    response_model=PaginatedProjects,
    status_code=status.HTTP_200_OK,
    summary="List visible projects (paginated)",
)
async def list_projects(
    project_service: ProjectServiceDep,
    current_user: OptionalUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedProjects:
    items, total = await project_service.list_visible(
        limit=limit, offset=offset, include_hidden=current_user is not None
    )
    return PaginatedProjects(
        items=[ProjectRead.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/link/{link}",
    response_model=ProjectRead,
    status_code=status.HTTP_200_OK,
    summary="Get a visible project by its link (slug)",
)
async def get_project_by_link(
    link: str,
    project_service: ProjectServiceDep,
    current_user: OptionalUser,
) -> ProjectRead:
    try:
        project = await project_service.get_visible_by_link(
            link, include_hidden=current_user is not None
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc
    return ProjectRead.model_validate(project)


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    status_code=status.HTTP_200_OK,
    summary="Get a visible project by id",
)
async def get_project(
    project_id: int,
    project_service: ProjectServiceDep,
    current_user: OptionalUser,
) -> ProjectRead:
    try:
        project = await project_service.get_visible(
            project_id, include_hidden=current_user is not None
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc
    return ProjectRead.model_validate(project)


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project (image via file or URL)",
    dependencies=protected,
)
async def create_project(
    project_service: ProjectServiceDep,
    name: Annotated[str, Form(min_length=1, max_length=512)],
    brief_description: Annotated[str, Form(min_length=1)],
    description: Annotated[str, Form(min_length=1)],
    url_project: Annotated[str, Form(min_length=1, max_length=2048)],
    category_ids: Annotated[list[int], Form(default_factory=list)],
    subcategory_ids: Annotated[list[int], Form(default_factory=list)],
    visible: Annotated[bool, Form()] = True,
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
) -> ProjectRead:
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
        project = await project_service.create(
            name=name,
            brief_description=brief_description,
            description=description,
            url_project=url_project,
            visible=visible,
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

    return ProjectRead.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    status_code=status.HTTP_200_OK,
    summary="Update a project (image optional via file or URL)",
    dependencies=protected,
)
async def update_project(
    project_id: int,
    project_service: ProjectServiceDep,
    name: Annotated[str | None, Form(min_length=1, max_length=512)] = None,
    brief_description: Annotated[str | None, Form(min_length=1)] = None,
    description: Annotated[str | None, Form(min_length=1)] = None,
    url_project: Annotated[str | None, Form(min_length=1, max_length=2048)] = None,
    visible: Annotated[bool | None, Form()] = None,
    category_ids: Annotated[list[int] | None, Form()] = None,
    subcategory_ids: Annotated[list[int] | None, Form()] = None,
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
) -> ProjectRead:
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
        project = await project_service.update(
            project_id=project_id,
            name=name,
            brief_description=brief_description,
            description=description,
            url_project=url_project,
            visible=visible,
            category_ids=category_ids,
            subcategory_ids=subcategory_ids,
            image_file=image_bytes,
            image_url=url,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
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

    return ProjectRead.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a project",
    dependencies=protected,
)
async def delete_project(
    project_id: int,
    project_service: ProjectServiceDep,
) -> Response:
    try:
        await project_service.delete(project_id=project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
