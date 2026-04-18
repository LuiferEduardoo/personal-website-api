from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.dependencies.auth import protected
from app.dependencies.db import AsyncDBSession
from app.repositories.category import CategoryRepository
from app.repositories.project import ProjectRepository
from app.repositories.subcategory import SubcategoryRepository
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project import ProjectNotFoundError, ProjectService
from app.services.taxonomy import InvalidCategoriesError, InvalidSubcategoriesError

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(session: AsyncDBSession) -> ProjectService:
    return ProjectService(
        project_repository=ProjectRepository(session),
        category_repository=CategoryRepository(session),
        subcategory_repository=SubcategoryRepository(session),
    )


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
    dependencies=protected,
)
async def create_project(
    payload: ProjectCreate,
    project_service: ProjectServiceDep,
) -> ProjectRead:
    try:
        project = await project_service.create(
            name=payload.name,
            brief_description=payload.brief_description,
            description=payload.description,
            url_project=payload.url_project,
            visible=payload.visible,
            category_ids=payload.category_ids,
            subcategory_ids=payload.subcategory_ids,
        )
    except InvalidCategoriesError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except InvalidSubcategoriesError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return ProjectRead.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    status_code=status.HTTP_200_OK,
    summary="Update a project",
    dependencies=protected,
)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    project_service: ProjectServiceDep,
) -> ProjectRead:
    try:
        project = await project_service.update(
            project_id=project_id,
            data=payload.model_dump(exclude_unset=True),
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
