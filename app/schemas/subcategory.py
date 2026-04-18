from app.schemas.base import TimestampSchema


class SubcategoryRead(TimestampSchema):
    id: int
    name: str
