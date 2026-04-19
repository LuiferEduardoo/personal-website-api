from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.category import Category
from app.models.image import Image
from app.models.subcategory import Subcategory

project_categories = Table(
    "project_categories",
    Base.metadata,
    Column(
        "project_id",
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

project_subcategories = Table(
    "project_subcategories",
    Base.metadata,
    Column(
        "project_id",
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "subcategory_id",
        ForeignKey("subcategories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Project(Base, IDMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    brief_description: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str] = mapped_column(Text, nullable=False)
    visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    url_project: Mapped[str] = mapped_column(Text, nullable=False)
    image_id: Mapped[int | None] = mapped_column(
        ForeignKey("images.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    image: Mapped[Image | None] = relationship("Image", lazy="selectin")
    categories: Mapped[list[Category]] = relationship(
        "Category", secondary=project_categories, lazy="selectin"
    )
    subcategories: Mapped[list[Subcategory]] = relationship(
        "Subcategory", secondary=project_subcategories, lazy="selectin"
    )
