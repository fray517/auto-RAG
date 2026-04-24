"""База знаний: блоки, чанки и векторы для RAG."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeBlock(Base):
    """
    Снимок для общей БЗ: название, три типа материалов.
    Один логический блок на задачу.
    """

    __tablename__ = "knowledge_blocks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_job_id: Mapped[int] = mapped_column(
        ForeignKey("video_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    video_title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    manual_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Chunk(Base):
    """Фрагмент для векторного поиска."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_block_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_type: Mapped[str] = mapped_column(String(32), nullable=False)
    section: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Embedding(Base):
    """Векторное представление чанка (JSON-массив в MVP)."""

    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    vector_dim: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vector_json: Mapped[str] = mapped_column(
        Text,
        default="[]",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
