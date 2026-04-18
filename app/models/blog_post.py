from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IDMixin, TimestampMixin
from app.models.user import User

blog_post_authors = Table(
    "blog_post_authors",
    Base.metadata,
    Column(
        "blog_post_id",
        ForeignKey("blog_posts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class BlogPost(Base, IDMixin, TimestampMixin):
    __tablename__ = "blog_posts"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str] = mapped_column(String(2048), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reading_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    user: Mapped[User] = relationship(
        "User", foreign_keys=[user_id], lazy="selectin"
    )
    authors: Mapped[list[User]] = relationship(
        "User", secondary=blog_post_authors, lazy="selectin"
    )
