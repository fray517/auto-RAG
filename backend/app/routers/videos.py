"""Загрузка и обработка видео."""

import mimetypes
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_temp_path
from app.core.responses import Utf8JSONResponse
from app.db.session import get_session
from app.domain.pipeline_stages import (
    STAGE_TRANSCRIPT_CLEANING,
    default_stage_for_uploaded,
    progress_for_stage_id,
)
from app.models.ocr_result import OcrResult
from app.models.transcripts import CleanTranscript, RawTranscript
from app.models.video_job import VideoJob
from app.pipeline.run_audio_job import run_audio_extraction_job
from app.schemas.video_results import (
    CleanTranscriptResponse,
    CleanTranscriptUpdateRequest,
    OcrResultItem,
    OcrResultsResponse,
    RawTranscriptResponse,
    RawTranscriptUpdateRequest,
    SlideCaptureRequest,
    SlideItem,
    SlidesResponse,
)
from app.schemas.video_status import VideoJobStatusResponse
from app.schemas.video_upload import VideoUploadResponse
from app.services.audio_ffmpeg import find_input_video
from app.services.clean_transcript_llm import clean_transcript
from app.services.keyframes_ffmpeg import extract_frame_at_timestamp

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
STATUS_FAILED = "failed"
STATUS_PROCESSING = "processing"

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


def _get_job_dir(job_id: int) -> Path:
    return (get_temp_path() / str(job_id)).resolve()


def _get_input_video_or_404(job_id: int) -> Path:
    try:
        return find_input_video(_get_job_dir(job_id))
    except FileNotFoundError as err:
        raise HTTPException(
            status_code=404,
            detail="Видео файл задачи не найден.",
        ) from err


def _slide_image_url(job_id: int, slide_id: int) -> str:
    return f"/videos/{job_id}/slides/{slide_id}/image"


def _slide_item(job_id: int, row: OcrResult) -> SlideItem:
    source_hint = row.source_hint or f"slide_{row.id}.jpg"
    return SlideItem(
        id=row.id,
        sort_order=row.sort_order,
        source_hint=source_hint,
        image_url=_slide_image_url(job_id, row.id),
    )


def _collect_ocr_text(job_id: int, db: Session) -> str:
    rows = db.execute(
        select(OcrResult)
        .where(OcrResult.video_job_id == job_id)
        .where(OcrResult.text.is_not(None))
        .order_by(OcrResult.sort_order, OcrResult.id),
    ).scalars()
    return "\n\n".join(row.text or "" for row in rows).strip()


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


@router.get("/{job_id}/file")
def get_video_file(
    job_id: int,
    db: Session = Depends(get_session),
) -> FileResponse:
    """Исходное видео для просмотра в браузере."""
    job = _get_job_or_404(job_id, db)
    video_path = _get_input_video_or_404(job_id)
    media_type, _ = mimetypes.guess_type(video_path.name)
    return FileResponse(
        path=video_path,
        media_type=media_type or "video/mp4",
        filename=job.filename,
    )


@router.get("/{job_id}/slides", response_model=SlidesResponse)
def get_slides(
    job_id: int,
    db: Session = Depends(get_session),
) -> SlidesResponse:
    """Список слайдов, которые пользователь сохранил вручную."""
    _get_job_or_404(job_id, db)
    rows = db.execute(
        select(OcrResult)
        .where(OcrResult.video_job_id == job_id)
        .where(OcrResult.source_hint.like("slide_%"))
        .order_by(OcrResult.sort_order, OcrResult.id),
    ).scalars()
    items = [_slide_item(job_id, row) for row in rows]
    return SlidesResponse(job_id=job_id, items=items)


@router.post("/{job_id}/slides", response_model=SlideItem)
def capture_slide(
    job_id: int,
    payload: SlideCaptureRequest,
    db: Session = Depends(get_session),
) -> SlideItem:
    """Сохранить кадр видео по текущей позиции плеера."""
    _get_job_or_404(job_id, db)
    video_path = _get_input_video_or_404(job_id)
    max_order = db.execute(
        select(func.max(OcrResult.sort_order)).where(
            OcrResult.video_job_id == job_id,
        ),
    ).scalar_one()
    sort_order = 0 if max_order is None else max_order + 1
    timestamp_tag = int(payload.timestamp_seconds * 1000)
    filename = f"slide_{sort_order:04d}_{timestamp_tag:010d}.jpg"
    output_path = _get_job_dir(job_id) / "slides" / filename

    try:
        extract_frame_at_timestamp(
            video_path=video_path,
            output_path=output_path,
            timestamp_seconds=payload.timestamp_seconds,
        )
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err

    row = OcrResult(
        video_job_id=job_id,
        sort_order=sort_order,
        source_hint=filename,
        text=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _slide_item(job_id, row)


@router.get("/{job_id}/slides/{slide_id}/image")
def get_slide_image(
    job_id: int,
    slide_id: int,
    db: Session = Depends(get_session),
) -> FileResponse:
    """Изображение сохранённого вручную слайда."""
    _get_job_or_404(job_id, db)
    row = db.get(OcrResult, slide_id)
    if row is None or row.video_job_id != job_id or not row.source_hint:
        raise HTTPException(status_code=404, detail="Слайд не найден")
    slide_path = (_get_job_dir(job_id) / "slides" / row.source_hint).resolve()
    try:
        slide_path.relative_to((_get_job_dir(job_id) / "slides").resolve())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Некорректный путь слайда.",
        ) from None
    if not slide_path.is_file():
        raise HTTPException(status_code=404, detail="Файл слайда не найден")
    return FileResponse(path=slide_path, media_type="image/jpeg")


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


@router.get(
    "/{job_id}/clean-transcript",
    response_model=CleanTranscriptResponse,
)
def get_clean_transcript(
    job_id: int,
    db: Session = Depends(get_session),
) -> CleanTranscriptResponse:
    """Получить очищенную транскрипцию, если она уже создана."""
    _get_job_or_404(job_id, db)
    clean = db.execute(
        select(CleanTranscript).where(
            CleanTranscript.video_job_id == job_id,
        ),
    ).scalar_one_or_none()
    return CleanTranscriptResponse(
        job_id=job_id,
        content=clean.content if clean is not None else None,
        updated_at=clean.updated_at if clean is not None else None,
    )


@router.put(
    "/{job_id}/clean-transcript",
    response_model=CleanTranscriptResponse,
)
def update_clean_transcript(
    job_id: int,
    payload: CleanTranscriptUpdateRequest,
    db: Session = Depends(get_session),
) -> CleanTranscriptResponse:
    """Сохранить ручные правки очищенной транскрипции."""
    _get_job_or_404(job_id, db)
    clean = db.execute(
        select(CleanTranscript).where(
            CleanTranscript.video_job_id == job_id,
        ),
    ).scalar_one_or_none()
    if clean is None:
        clean = CleanTranscript(
            video_job_id=job_id,
            content=payload.content,
        )
        db.add(clean)
    else:
        clean.content = payload.content

    db.commit()
    db.refresh(clean)
    return CleanTranscriptResponse(
        job_id=job_id,
        content=clean.content,
        updated_at=clean.updated_at,
    )


@router.post(
    "/{job_id}/clean-transcript/generate",
    response_model=CleanTranscriptResponse,
)
def generate_clean_transcript(
    job_id: int,
    db: Session = Depends(get_session),
) -> CleanTranscriptResponse:
    """Сгенерировать clean transcript из raw transcript и OCR-контекста."""
    job = _get_job_or_404(job_id, db)
    raw = db.execute(
        select(RawTranscript).where(RawTranscript.video_job_id == job_id),
    ).scalar_one_or_none()
    if raw is None or not (raw.content or "").strip():
        raise HTTPException(
            status_code=409,
            detail="Сырая транскрипция ещё не готова.",
        )

    job.status = STATUS_PROCESSING
    job.current_stage = STAGE_TRANSCRIPT_CLEANING
    job.progress_percent = progress_for_stage_id(STAGE_TRANSCRIPT_CLEANING)
    job.last_error = None
    db.commit()

    try:
        clean_text = clean_transcript(
            raw_text=raw.content or "",
            ocr_text=_collect_ocr_text(job_id, db),
        )
    except RuntimeError as err:
        job = db.get(VideoJob, job_id)
        if job is not None:
            job.status = STATUS_FAILED
            job.last_error = str(err)[:2000]
            db.commit()
        raise HTTPException(status_code=500, detail=str(err)) from err

    clean = db.execute(
        select(CleanTranscript).where(
            CleanTranscript.video_job_id == job_id,
        ),
    ).scalar_one_or_none()
    if clean is None:
        clean = CleanTranscript(video_job_id=job_id, content=clean_text)
        db.add(clean)
    else:
        clean.content = clean_text

    db.commit()
    db.refresh(clean)
    return CleanTranscriptResponse(
        job_id=job_id,
        content=clean.content,
        updated_at=clean.updated_at,
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
