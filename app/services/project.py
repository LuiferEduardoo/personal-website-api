from datetime import datetime, timezone
from typing import Any

from app.core.text import slugify
from app.models.project import Project
from app.repositories.category import CategoryRepository
from app.repositories.project import ProjectRepository
from app.repositories.subcategory import SubcategoryRepository
from app.services.taxonomy import fetch_categories, fetch_subcategories


class ProjectNotFoundError(Exception):
    """Raised when a project cannot be found or is soft-deleted."""


_SIMPLE_FIELDS = ("brief_description", "description", "url_project", "visible")


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        category_repository: CategoryRepository,
        subcategory_repository: SubcategoryRepository,
    ) -> None:
        self.project_repository = project_repository
        self.category_repository = category_repository
        self.subcategory_repository = subcategory_repository

    async def create(
        self,
        *,
        name: str,
        brief_description: str,
        description: str,
        url_project: str,
        visible: bool,
        category_ids: list[int],
        subcategory_ids: list[int],
    ) -> Project:
        categories = await fetch_categories(self.category_repository, category_ids)
        subcategories = await fetch_subcategories(
            self.subcategory_repository, subcategory_ids
        )

        project = Project(
            name=name,
            brief_description=brief_description,
            description=description,
            link=slugify(name),
            url_project=url_project,
            visible=visible,
        )
        project.categories = list(categories)
        project.subcategories = list(subcategories)

        session = self.project_repository.session
        session.add(project)
        await session.flush()
        await session.refresh(project, ["created_at", "updated_at"])
        await session.commit()
        return project

    async def update(self, *, project_id: int, data: dict[str, Any]) -> Project:
        project = await self.project_repository.get_active(project_id)
        if project is None:
            raise ProjectNotFoundError()

        if "category_ids" in data:
            categories = await fetch_categories(
                self.category_repository, data["category_ids"]
            )
            project.categories = list(categories)
        if "subcategory_ids" in data:
            subcategories = await fetch_subcategories(
                self.subcategory_repository, data["subcategory_ids"]
            )
            project.subcategories = list(subcategories)

        if "name" in data:
            project.name = data["name"]
            project.link = slugify(data["name"])
        for key in _SIMPLE_FIELDS:
            if key in data:
                setattr(project, key, data[key])

        session = self.project_repository.session
        await session.flush()
        await session.refresh(project, ["updated_at"])
        await session.commit()
        return project

    async def list_visible(
        self, *, limit: int, offset: int
    ) -> tuple[list[Project], int]:
        items = await self.project_repository.list_visible(limit, offset)
        total = await self.project_repository.count_visible()
        return items, total

    async def get_visible(self, project_id: int) -> Project:
        project = await self.project_repository.get_visible(project_id)
        if project is None:
            raise ProjectNotFoundError()
        return project

    async def get_visible_by_link(self, link: str) -> Project:
        project = await self.project_repository.get_visible_by_link(link)
        if project is None:
            raise ProjectNotFoundError()
        return project

    async def delete(self, *, project_id: int) -> None:
        project = await self.project_repository.get_active(project_id)
        if project is None:
            raise ProjectNotFoundError()

        project.deleted_at = datetime.now(timezone.utc)
        await self.project_repository.session.commit()
