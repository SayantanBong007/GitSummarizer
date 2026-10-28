"""add step_log to analyses

Revision ID: 0002_step_log
Revises: 0001_initial
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_step_log"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("step_log", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "step_log")
