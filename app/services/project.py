from collections.abc import Sequence
from datetime import datetime, timezone

from app.core.text import slugify
from app.models.image import Image
from app.models.project import Project
from app.repositories.category import CategoryRepository
from app.repositories.project import ProjectRepository
from app.repositories.subcategory import SubcategoryRepository
from app.services.image import ImageService
from app.services.taxonomy import fetch_categories, fetch_subcategories


class ProjectNotFoundError(Exception):
    """Raised when a project cannot be found or is soft-deleted."""


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        category_repository: CategoryRepository,
        subcategory_repository: SubcategoryRepository,
        image_service: ImageService,
    ) -> None:
        self.project_repository = project_repository
        self.category_repository = category_repository
        self.subcategory_repository = subcategory_repository
        self.image_service = image_service

    async def create(
        self,
        *,
        name: str,
        brief_description: str,
        description: str,
        url_project: str,
        visible: bool,
        category_ids: Sequence[int],
        subcategory_ids: Sequence[int],
        image_file: bytes | None = None,
        image_url: str | None = None,
    ) -> Project:
        categories = await fetch_categories(self.category_repository, category_ids)
        subcategories = await fetch_subcategories(
            self.subcategory_repository, subcategory_ids
        )
        image = await self._build_image(image_file, image_url)

        project = Project(
            name=name,
            brief_description=brief_description,
            description=description,
            link=slugify(name),
            url_project=url_project,
            visible=visible,
            image_id=image.id,
        )
        project.image = image
        project.categories = list(categories)
        project.subcategories = list(subcategories)

        session = self.project_repository.session
        session.add(project)
        await session.flush()
        await session.refresh(project, ["created_at", "updated_at"])
        await session.commit()
        return project

    async def update(
        self,
        *,
        project_id: int,
        name: str | None = None,
        brief_description: str | None = None,
        description: str | None = None,
        url_project: str | None = None,
        visible: bool | None = None,
        category_ids: Sequence[int] | None = None,
        subcategory_ids: Sequence[int] | None = None,
        image_file: bytes | None = None,
        image_url: str | None = None,
    ) -> Project:
        project = await self.project_repository.get_active(project_id)
        if project is None:
            raise ProjectNotFoundError()

        if category_ids is not None:
            categories = await fetch_categories(
                self.category_repository, category_ids
            )
            project.categories = list(categories)
        if subcategory_ids is not None:
            subcategories = await fetch_subcategories(
                self.subcategory_repository, subcategory_ids
            )
            project.subcategories = list(subcategories)

        if name is not None:
            project.name = name
            project.link = slugify(name)
        if brief_description is not None:
            project.brief_description = brief_description
        if description is not None:
            project.description = description
        if url_project is not None:
            project.url_project = url_project
        if visible is not None:
            project.visible = visible

        if image_file is not None or image_url is not None:
            image = await self._build_image(image_file, image_url)
            project.image = image
            project.image_id = image.id

        session = self.project_repository.session
        await session.flush()
        await session.refresh(project, ["updated_at"])
        await session.commit()
        return project

    async def list_visible(
        self, *, limit: int, offset: int, include_hidden: bool = False
    ) -> tuple[list[Project], int]:
        items = await self.project_repository.list_visible(
            limit, offset, include_hidden=include_hidden
        )
        total = await self.project_repository.count_visible(
            include_hidden=include_hidden
        )
        return items, total

    async def get_visible(
        self, project_id: int, *, include_hidden: bool = False
    ) -> Project:
        project = await self.project_repository.get_visible(
            project_id, include_hidden=include_hidden
        )
        if project is None:
            raise ProjectNotFoundError()
        return project

    async def get_visible_by_link(
        self, link: str, *, include_hidden: bool = False
    ) -> Project:
        project = await self.project_repository.get_visible_by_link(
            link, include_hidden=include_hidden
        )
        if project is None:
            raise ProjectNotFoundError()
        return project

    async def delete(self, *, project_id: int) -> None:
        project = await self.project_repository.get_active(project_id)
        if project is None:
            raise ProjectNotFoundError()

        project.deleted_at = datetime.now(timezone.utc)
        await self.project_repository.session.commit()

    async def _build_image(
        self, image_file: bytes | None, image_url: str | None
    ) -> Image:
        if image_file is not None:
            return await self.image_service.upload(image_file, folder="projects")
        assert image_url is not None
        return await self.image_service.upload_from_url(image_url, folder="projects")
