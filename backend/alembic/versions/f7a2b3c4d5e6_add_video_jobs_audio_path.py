"""add video_jobs audio_path (шаг 3.1)

Revision ID: f7a2b3c4d5e6
Revises: 91d83818410b
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a2b3c4d5e6"
down_revision: Union[str, None] = "91d83818410b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "video_jobs",
        sa.Column("audio_path", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("video_jobs", "audio_path")
