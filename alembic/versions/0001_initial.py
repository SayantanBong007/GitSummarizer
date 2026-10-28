"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("default_branch", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("stars", sa.Integer, nullable=True),
        sa.Column("local_path", sa.String(1024), nullable=True),
        sa.Column("languages", sa.JSON, nullable=True),
        sa.Column("frameworks", sa.JSON, nullable=True),
        sa.Column("clone_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_repositories_url", "repositories", ["url"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "repository_id",
            sa.String(36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Float, nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("tech_stack", sa.JSON, nullable=True),
        sa.Column("architecture_report", sa.JSON, nullable=True),
        sa.Column("module_breakdown", sa.JSON, nullable=True),
        sa.Column("api_report", sa.JSON, nullable=True),
        sa.Column("database_report", sa.JSON, nullable=True),
        sa.Column("frontend_report", sa.JSON, nullable=True),
        sa.Column("security_report", sa.JSON, nullable=True),
        sa.Column("design_patterns", sa.JSON, nullable=True),
        sa.Column("dependency_graph", sa.JSON, nullable=True),
        sa.Column("diagrams", sa.JSON, nullable=True),
        sa.Column("executive_summary", sa.Text, nullable=True),
        sa.Column("markdown_docs", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_analyses_repository_id", "analyses", ["repository_id"])
    op.create_index("ix_analyses_celery_task_id", "analyses", ["celery_task_id"])


def downgrade() -> None:
    op.drop_table("analyses")
    op.drop_table("repositories")
