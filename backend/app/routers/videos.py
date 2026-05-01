"""Загрузка и обработка видео."""

from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_temp_path
from app.core.responses import Utf8JSONResponse
from app.db.session import get_session
from app.domain.pipeline_stages import default_stage_for_uploaded
from app.models.ocr_result import OcrResult
from app.models.transcripts import RawTranscript
from app.models.video_job import VideoJob
from app.pipeline.run_audio_job import run_audio_extraction_job
from app.schemas.video_results import (
    OcrResultItem,
    OcrResultsResponse,
    RawTranscriptResponse,
    RawTranscriptUpdateRequest,
)
from app.schemas.video_status import VideoJobStatusResponse
from app.schemas.video_upload import VideoUploadResponse

router = APIRouter(
    prefix="/videos",
    tags=["videos"],
    default_response_class=Utf8JSONResponse,
)

ALLOWED_VIDEO_SUFFIXES = frozenset({
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
})

STATUS_UPLOADED = "uploaded"

_READ_CHUNK = 1024 * 1024


def _status_payload(job: VideoJob) -> VideoJobStatusResponse:
    """Собрать ответ; для старых записей — fallback по status."""
    stage = job.current_stage
    progress = job.progress_percent
    if stage is None and job.status == STATUS_UPLOADED:
        stage_name, pr = default_stage_for_uploaded()
        stage, progress = stage_name, pr
    if not stage:
        stage = "unknown"
    return VideoJobStatusResponse(
        job_id=job.id,
        status=job.status,
        stage=stage,
        progress_percent=progress,
        error=job.last_error,
    )


def _safe_client_name(name: str) -> str:
    """Только имя файла, без путей."""
    base = Path(name).name
    if not base or base in (".", ".."):
        return "video"
    return base


def _get_job_or_404(job_id: int, db: Session) -> VideoJob:
    """Вернуть задачу или единообразный 404."""
    job = db.get(VideoJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return job


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Один видеофайл"),
    db: Session = Depends(get_session),
) -> VideoUploadResponse:
    """
    Принять ровно один файл, проверить расширение, сохранить в TEMP,
    создать запись `video_jobs` со статусом `uploaded`.
    """
    client_name = _safe_client_name(file.filename or "")
    ext = Path(client_name).suffix.lower()
    if ext not in ALLOWED_VIDEO_SUFFIXES:
        await file.close()
        raise HTTPException(
            status_code=400,
            detail=(
                "Недопустимое расширение. Допустимы: "
                "mp4, mov, avi, mkv, webm."
            ),
        )

    stage_name, pr = default_stage_for_uploaded()
    job = VideoJob(
        filename=client_name,
        status=STATUS_UPLOADED,
        current_stage=stage_name,
        progress_percent=pr,
        last_error=None,
    )
    db.add(job)
    db.flush()

    temp_root = get_temp_path()
    job_dir = temp_root / str(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"input{ext}"
    dest_abs = (job_dir / stored_name).resolve()
    try:
        dest_abs.relative_to(job_dir.resolve())
    except ValueError:
        db.rollback()
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Некорректное имя файла.",
        ) from None

    try:
        with dest_abs.open("wb") as out:
            while True:
                chunk = await file.read(_READ_CHUNK)
                if not chunk:
                    break
                out.write(chunk)
    except OSError as err:
        db.rollback()
        dest_abs.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось сохранить файл: {err}",
        ) from err
    finally:
        await file.close()

    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_audio_extraction_job, job.id)

    rel = f"{job.id}/{stored_name}"
    return VideoUploadResponse(
        job_id=job.id,
        status=job.status,
        filename=job.filename,
        stored_path=rel,
    )


@router.get("/{job_id}/status", response_model=VideoJobStatusResponse)
def get_video_job_status(
    job_id: int,
    db: Session = Depends(get_session),
) -> VideoJobStatusResponse:
    """Текущий статус, этап, прогресс и ошибка (если были)."""
    job = _get_job_or_404(job_id, db)
    return _status_payload(job)


@router.get(
    "/{job_id}/raw-transcript",
    response_model=RawTranscriptResponse,
)
def get_raw_transcript(
    job_id: int,
    db: Session = Depends(get_session),
) -> RawTranscriptResponse:
    """Сырой транскрипт, если этап транскрибации уже сохранил результат."""
    _get_job_or_404(job_id, db)
    raw = db.execute(
        select(RawTranscript).where(RawTranscript.video_job_id == job_id),
    ).scalar_one_or_none()
    return RawTranscriptResponse(
        job_id=job_id,
        content=raw.content if raw is not None else None,
        updated_at=raw.updated_at if raw is not None else None,
    )


@router.put(
    "/{job_id}/raw-transcript",
    response_model=RawTranscriptResponse,
)
def update_raw_transcript(
    job_id: int,
    payload: RawTranscriptUpdateRequest,
    db: Session = Depends(get_session),
) -> RawTranscriptResponse:
    """Сохранить ручные правки сырой транскрипции."""
    _get_job_or_404(job_id, db)
    raw = db.execute(
        select(RawTranscript).where(RawTranscript.video_job_id == job_id),
    ).scalar_one_or_none()
    if raw is None:
        raw = RawTranscript(
            video_job_id=job_id,
            content=payload.content,
        )
        db.add(raw)
    else:
        raw.content = payload.content

    db.commit()
    db.refresh(raw)
    return RawTranscriptResponse(
        job_id=job_id,
        content=raw.content,
        updated_at=raw.updated_at,
    )


@router.get("/{job_id}/ocr", response_model=OcrResultsResponse)
def get_ocr_results(
    job_id: int,
    db: Session = Depends(get_session),
) -> OcrResultsResponse:
    """OCR-результаты по ключевым кадрам в порядке обработки."""
    _get_job_or_404(job_id, db)
    rows = db.execute(
        select(OcrResult)
        .where(OcrResult.video_job_id == job_id)
        .order_by(OcrResult.sort_order, OcrResult.id),
    ).scalars()
    items = [
        OcrResultItem(
            id=row.id,
            sort_order=row.sort_order,
            source_hint=row.source_hint,
            text=row.text,
        )
        for row in rows
    ]
    return OcrResultsResponse(job_id=job_id, items=items)
