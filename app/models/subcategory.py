from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin


class Subcategory(Base, IDMixin, TimestampMixin):
    __tablename__ = "subcategories"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
