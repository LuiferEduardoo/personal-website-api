from datetime import datetime

from pydantic import EmailStr

from app.schemas.base import TimestampSchema
from app.schemas.image import ImageRead


class UserRead(TimestampSchema):
    id: int
    name: str
    email: EmailStr
    email_verified_at: datetime | None
    profile_photo_id: int | None
    profile_photo: ImageRead | None
