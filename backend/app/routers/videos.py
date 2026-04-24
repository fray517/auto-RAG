"""Загрузка и обработка видео."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_temp_path
from app.db.session import get_session
from app.models.video_job import VideoJob
from app.schemas.video_upload import VideoUploadResponse

router = APIRouter(prefix="/videos", tags=["videos"])

ALLOWED_VIDEO_SUFFIXES = frozenset({
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
})

STATUS_UPLOADED = "uploaded"

_READ_CHUNK = 1024 * 1024


def _safe_client_name(name: str) -> str:
    """Только имя файла, без путей."""
    base = Path(name).name
    if not base or base in (".", ".."):
        return "video"
    return base


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
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

    job = VideoJob(
        filename=client_name,
        status=STATUS_UPLOADED,
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

    rel = f"{job.id}/{stored_name}"
    return VideoUploadResponse(
        job_id=job.id,
        status=job.status,
        filename=job.filename,
        stored_path=rel,
    )
