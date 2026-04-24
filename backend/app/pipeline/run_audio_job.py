"""Фоновая задача: извлечение аудио (план, шаг 3.1)."""

import logging

from app.core.config import get_temp_path
from app.db.session import create_db_session
from app.domain.pipeline_stages import (
    STAGE_AUDIO_EXTRACTION,
    STAGE_FRAME_ANALYSIS,
    progress_for_stage_id,
)
from app.models.video_job import VideoJob
from app.services.audio_ffmpeg import extract_audio_wav, find_input_video

log = logging.getLogger(__name__)

STATUS_PROCESSING = "processing"
STATUS_FAILED = "failed"


def run_audio_extraction_job(job_id: int) -> None:
    """
    Статус: processing, этап audio_extraction; по успеху — путь к WAV,
    этап frame_analysis (следующий в плане — 3.2).
    """
    db = create_db_session()
    try:
        job = db.get(VideoJob, job_id)
        if job is None:
            log.warning("Видеозадача id=%s не найдена", job_id)
            return
        job.status = STATUS_PROCESSING
        job.current_stage = STAGE_AUDIO_EXTRACTION
        job.progress_percent = progress_for_stage_id(
            STAGE_AUDIO_EXTRACTION,
        )
        job.last_error = None
        db.commit()

        temp = get_temp_path()
        job_dir = (temp / str(job_id)).resolve()
        video_path = find_input_video(job_dir)
        audio_abs = job_dir / "audio.wav"
        extract_audio_wav(video_path, audio_abs)

        job = db.get(VideoJob, job_id)
        if job is None:
            return
        rel = f"{job_id}/audio.wav"
        job.audio_path = rel
        job.current_stage = STAGE_FRAME_ANALYSIS
        job.progress_percent = progress_for_stage_id(
            STAGE_FRAME_ANALYSIS,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception("Сбой извлечения аудио job_id=%s", job_id)
        try:
            job = db.get(VideoJob, job_id)
            if job is not None:
                job.last_error = str(exc)[:2000]
                job.status = STATUS_FAILED
                job.current_stage = STAGE_AUDIO_EXTRACTION
                db.commit()
        except Exception:  # noqa: BLE001
            log.exception("Не удалось записать ошибку job_id=%s", job_id)
    finally:
        db.close()
