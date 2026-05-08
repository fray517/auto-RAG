"""Удаление данных и служебных файлов одной video job."""

import shutil
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_temp_path
from app.models.knowledge import Chunk, Embedding, KnowledgeBlock
from app.models.materials import Checklist, ManualGuide, Summary
from app.models.ocr_result import OcrResult
from app.models.transcripts import CleanTranscript, RawTranscript
from app.models.video_job import VideoJob
from app.models.visualization import Visualization


class JobCleanupError(RuntimeError):
    """Не удалось удалить служебные файлы job."""


def _delete_count(result) -> int:
    return int(result.rowcount or 0)


def _job_dir(job_id: int) -> Path:
    return (get_temp_path() / str(job_id)).resolve()


def delete_job_files(job_id: int) -> list[str]:
    """Удалить рабочую папку job внутри TEMP_PATH."""
    temp_root = get_temp_path().resolve()
    job_dir = _job_dir(job_id)
    try:
        job_dir.relative_to(temp_root)
    except ValueError as err:
        raise JobCleanupError("Некорректный путь служебных файлов.") from err

    if not job_dir.exists():
        return []
    try:
        shutil.rmtree(job_dir)
    except OSError as err:
        raise JobCleanupError(f"Не удалось удалить {job_dir}: {err}") from err
    return [str(job_dir)]


def delete_job_records(job_id: int, db: Session) -> dict[str, int]:
    """Удалить связанные записи без надежды на включённый FK cascade."""
    block_ids = list(
        db.execute(
            select(KnowledgeBlock.id).where(
                KnowledgeBlock.video_job_id == job_id,
            ),
        ).scalars(),
    )
    chunk_ids: list[int] = []
    if block_ids:
        chunk_ids = list(
            db.execute(
                select(Chunk.id).where(
                    Chunk.knowledge_block_id.in_(block_ids),
                ),
            ).scalars(),
        )

    counts: dict[str, int] = {}
    if chunk_ids:
        counts["embeddings"] = _delete_count(
            db.execute(
                delete(Embedding).where(Embedding.chunk_id.in_(chunk_ids)),
            ),
        )
    else:
        counts["embeddings"] = 0

    if block_ids:
        counts["chunks"] = _delete_count(
            db.execute(
                delete(Chunk).where(Chunk.knowledge_block_id.in_(block_ids)),
            ),
        )
        counts["knowledge_blocks"] = _delete_count(
            db.execute(
                delete(KnowledgeBlock).where(KnowledgeBlock.id.in_(block_ids)),
            ),
        )
    else:
        counts["chunks"] = 0
        counts["knowledge_blocks"] = 0

    table_deletes = [
        ("raw_transcripts", RawTranscript),
        ("clean_transcripts", CleanTranscript),
        ("ocr_results", OcrResult),
        ("summaries", Summary),
        ("manual_guides", ManualGuide),
        ("checklists", Checklist),
        ("visualizations", Visualization),
    ]
    for key, model in table_deletes:
        counts[key] = _delete_count(
            db.execute(delete(model).where(model.video_job_id == job_id)),
        )

    counts["video_jobs"] = _delete_count(
        db.execute(delete(VideoJob).where(VideoJob.id == job_id)),
    )
    db.commit()
    return counts
