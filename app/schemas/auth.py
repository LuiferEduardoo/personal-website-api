import re

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import BaseSchema

PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z\d]).{8,}$"
)
PASSWORD_ERROR_MESSAGE = (
    "Password must be at least 8 characters and contain at least one "
    "lowercase letter, one uppercase letter, one digit, and one special character."
)


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=255)


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChangeRequest(BaseSchema):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError(PASSWORD_ERROR_MESSAGE)
        return value
