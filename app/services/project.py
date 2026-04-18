from app.core.text import slugify
from app.models.project import Project
from app.repositories.category import CategoryRepository
from app.repositories.project import ProjectRepository
from app.repositories.subcategory import SubcategoryRepository
from app.services.taxonomy import fetch_categories, fetch_subcategories


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
