from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from backend.models.db.analysis import Analysis


class Repository(Base, TimestampMixin):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    stars: Mapped[int | None] = mapped_column()
    local_path: Mapped[str | None] = mapped_column(String(1024))
    languages: Mapped[list[str] | None] = mapped_column(JSON)
    frameworks: Mapped[list[str] | None] = mapped_column(JSON)
    clone_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | cloning | cloned | error

    analyses: Mapped[list[Analysis]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        lazy="select",
    )
