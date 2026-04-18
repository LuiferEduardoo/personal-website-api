from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.image import ImageRead


class UserRead(TimestampSchema):
    id: int
    name: str
    email: EmailStr
    email_verified_at: datetime | None
    profile_photo_id: int | None
    profile_photo: ImageRead | None


class UserUpdateMe(BaseSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
