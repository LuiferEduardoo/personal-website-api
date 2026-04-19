from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.category import CategoryRead
from app.schemas.image import ImageRead
from app.schemas.subcategory import SubcategoryRead


class ProjectRead(TimestampSchema):
    id: int
    name: str
    brief_description: str
    description: str
    link: str
    visible: bool
    url_project: str
    image: ImageRead | None
    categories: list[CategoryRead]
    subcategories: list[SubcategoryRead]


class PaginatedProjects(BaseSchema):
    items: list[ProjectRead]
    total: int
    limit: int
    offset: int
