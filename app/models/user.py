from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.image import Image


class User(Base, IDMixin, TimestampMixin):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Stores a hash (bcrypt/argon2), never plaintext. Hashing happens at the service layer.
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    remember_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_photo_id: Mapped[int | None] = mapped_column(
        ForeignKey("images.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    profile_photo: Mapped[Image | None] = relationship("Image", lazy="selectin")
