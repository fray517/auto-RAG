"""add video_jobs key_frames_count (шаг 3.2)

Revision ID: b8c3d4e5f6a0
Revises: f7a2b3c4d5e6
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c3d4e5f6a0"
down_revision: Union[str, None] = "f7a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "video_jobs",
        sa.Column("key_frames_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("video_jobs", "key_frames_count")
