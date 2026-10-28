from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from backend.models.db.repository import Repository


class Analysis(Base, TimestampMixin):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="queued"
    )  # queued | running | completed | failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_step: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True)

    # Analysis outputs (stored as JSON)
    tech_stack: Mapped[dict | None] = mapped_column(JSON)
    architecture_report: Mapped[dict | None] = mapped_column(JSON)
    module_breakdown: Mapped[dict | None] = mapped_column(JSON)
    api_report: Mapped[dict | None] = mapped_column(JSON)
    database_report: Mapped[dict | None] = mapped_column(JSON)
    frontend_report: Mapped[dict | None] = mapped_column(JSON)
    security_report: Mapped[dict | None] = mapped_column(JSON)
    design_patterns: Mapped[dict | None] = mapped_column(JSON)
    dependency_graph: Mapped[dict | None] = mapped_column(JSON)
    diagrams: Mapped[dict | None] = mapped_column(JSON)  # {name: mermaid_code}

    # Generated documentation
    executive_summary: Mapped[str | None] = mapped_column(Text)
    markdown_docs: Mapped[dict | None] = mapped_column(JSON)  # {filename: content}

    # Live progress log — list of StepEvent dicts, one per agent node
    step_log: Mapped[list | None] = mapped_column(JSON)

    repository: Mapped[Repository] = relationship(back_populates="analyses")
