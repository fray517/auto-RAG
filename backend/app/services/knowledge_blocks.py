"""Сборка knowledge block из итоговых материалов одной video job."""

from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeBlock
from app.models.materials import Checklist, ManualGuide, Summary
from app.models.video_job import VideoJob


class MissingMaterialError(RuntimeError):
    """Не все материалы готовы для сборки блока знаний."""


@dataclass(frozen=True)
class KnowledgeBlockDraft:
    """Текстовый снимок блока знаний перед сохранением."""

    video_job_id: int
    video_title: str
    summary_text: str
    manual_text: str
    checklist_text: str


@dataclass(frozen=True)
class KnowledgePreview:
    """Предпросмотр добавления блока в master-представление."""

    draft: KnowledgeBlockDraft
    current_master_text: str
    new_block_text: str
    next_master_text: str
    diff_text: str


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _video_title(filename: str) -> str:
    title = Path(filename).stem.strip()
    return title or filename.strip() or "Без названия"


def _require_material(name: str, value: str | None) -> str:
    text = _clean_text(value)
    if not text:
        raise MissingMaterialError(f"Материал не готов: {name}.")
    return text


def collect_knowledge_block_draft(
    job_id: int,
    db: Session,
) -> KnowledgeBlockDraft:
    """Собрать актуальные материалы job без записи в БД."""
    job = db.get(VideoJob, job_id)
    if job is None:
        raise ValueError("Video job не найдена.")

    summary = db.execute(
        select(Summary).where(Summary.video_job_id == job_id),
    ).scalar_one_or_none()
    manual = db.execute(
        select(ManualGuide).where(ManualGuide.video_job_id == job_id),
    ).scalar_one_or_none()
    checklist = db.execute(
        select(Checklist).where(Checklist.video_job_id == job_id),
    ).scalar_one_or_none()

    summary_text = _require_material(
        "конспект",
        summary.content if summary is not None else None,
    )
    manual_text = _require_material(
        "методичка",
        manual.content if manual is not None else None,
    )
    checklist_text = _require_material(
        "чек-лист",
        checklist.content if checklist is not None else None,
    )

    return KnowledgeBlockDraft(
        video_job_id=job_id,
        video_title=_video_title(job.filename),
        summary_text=summary_text,
        manual_text=manual_text,
        checklist_text=checklist_text,
    )


def render_knowledge_block(
    block: KnowledgeBlock | KnowledgeBlockDraft,
) -> str:
    """Сформировать текстовое представление блока для diff и master."""
    return (
        f"# {block.video_title}\n\n"
        "## Конспект\n\n"
        f"{_clean_text(block.summary_text)}\n\n"
        "## Методичка\n\n"
        f"{_clean_text(block.manual_text)}\n\n"
        "## Чек-лист\n\n"
        f"{_clean_text(block.checklist_text)}"
    ).strip()


def render_master_text(
    db: Session,
    exclude_job_id: int | None = None,
) -> str:
    """Собрать текущее master-представление из сохранённых блоков."""
    query = select(KnowledgeBlock).order_by(KnowledgeBlock.id)
    if exclude_job_id is not None:
        query = query.where(KnowledgeBlock.video_job_id != exclude_job_id)
    blocks = db.execute(query).scalars()
    parts = [render_knowledge_block(block) for block in blocks]
    return "\n\n---\n\n".join(part for part in parts if part).strip()


def build_knowledge_preview(job_id: int, db: Session) -> KnowledgePreview:
    """Показать diff между текущим master и master с новым блоком."""
    draft = collect_knowledge_block_draft(job_id, db)
    current_master = render_master_text(db, exclude_job_id=job_id)
    new_block = render_knowledge_block(draft)
    if current_master:
        next_master = f"{current_master}\n\n---\n\n{new_block}"
    else:
        next_master = new_block
    diff_lines = unified_diff(
        current_master.splitlines(),
        next_master.splitlines(),
        fromfile="master-current",
        tofile=f"master-with-job-{job_id}",
        lineterm="",
    )
    return KnowledgePreview(
        draft=draft,
        current_master_text=current_master,
        new_block_text=new_block,
        next_master_text=next_master,
        diff_text="\n".join(diff_lines),
    )


def build_knowledge_block(job_id: int, db: Session) -> KnowledgeBlock:
    """Создать или обновить knowledge block по итоговым материалам job."""
    draft = collect_knowledge_block_draft(job_id, db)

    block = db.execute(
        select(KnowledgeBlock).where(KnowledgeBlock.video_job_id == job_id),
    ).scalar_one_or_none()
    if block is None:
        block = KnowledgeBlock(video_job_id=job_id)
        db.add(block)

    block.video_title = draft.video_title
    block.summary_text = draft.summary_text
    block.manual_text = draft.manual_text
    block.checklist_text = draft.checklist_text

    db.commit()
    db.refresh(block)
    return block


def add_knowledge_block(job_id: int, db: Session) -> KnowledgeBlock:
    """Подтвердить добавление блока в общую базу знаний."""
    block = build_knowledge_block(job_id, db)

    # Chunks являются производными от блока, поэтому пересобираем их
    # после явного подтверждения добавления в БЗ.
    from app.services.chunking import rebuild_chunks_for_block

    rebuild_chunks_for_block(block, db)
    db.refresh(block)
    return block
