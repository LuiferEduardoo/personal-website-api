from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime
