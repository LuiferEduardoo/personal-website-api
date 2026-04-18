from datetime import datetime

from app.schemas.base import TimestampSchema


class ImageRead(TimestampSchema):
    id: int
    name: str
    folder: str | None
    url: str
    removed_at: datetime | None
