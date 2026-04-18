from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.category import CategoryRead
from app.schemas.subcategory import SubcategoryRead


class ProjectCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=512)
    brief_description: str = Field(min_length=1)
    description: str = Field(min_length=1)
    url_project: str = Field(min_length=1, max_length=2048)
    visible: bool = True
    category_ids: list[int] = Field(default_factory=list)
    subcategory_ids: list[int] = Field(default_factory=list)


class ProjectUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=512)
    brief_description: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    url_project: str | None = Field(default=None, min_length=1, max_length=2048)
    visible: bool | None = None
    category_ids: list[int] | None = None
    subcategory_ids: list[int] | None = None


class ProjectRead(TimestampSchema):
    id: int
    name: str
    brief_description: str
    description: str
    link: str
    visible: bool
    url_project: str
    categories: list[CategoryRead]
    subcategories: list[SubcategoryRead]


class PaginatedProjects(BaseSchema):
    items: list[ProjectRead]
    total: int
    limit: int
    offset: int
