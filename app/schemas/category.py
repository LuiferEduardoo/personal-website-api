from app.schemas.base import TimestampSchema


class CategoryRead(TimestampSchema):
    id: int
    name: str
