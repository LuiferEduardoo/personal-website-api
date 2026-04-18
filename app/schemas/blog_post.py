from datetime import time

from pydantic import EmailStr

from app.schemas.base import TimestampSchema
from app.schemas.category import CategoryRead
from app.schemas.image import ImageRead
from app.schemas.subcategory import SubcategoryRead


class AuthorBrief(TimestampSchema):
    id: int
    name: str
    email: EmailStr


class BlogPostRead(TimestampSchema):
    id: int
    title: str
    content: str
    link: str
    reading_time: time | None
    visible: bool
    user: AuthorBrief
    cover_image: ImageRead | None
    authors: list[AuthorBrief]
    categories: list[CategoryRead]
    subcategories: list[SubcategoryRead]
