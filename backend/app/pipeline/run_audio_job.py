"""Фоновая задача: аудио (3.1) и ключевые кадры (3.2)."""

import logging

from app.core.config import get_temp_path
from app.db.session import create_db_session
from app.domain.pipeline_stages import (
    STAGE_AUDIO_EXTRACTION,
    STAGE_FRAME_ANALYSIS,
    STAGE_TRANSCRIPTION,
    progress_for_stage_id,
)
from app.models.video_job import VideoJob
from app.services.audio_ffmpeg import extract_audio_wav, find_input_video
from app.services.keyframes_ffmpeg import extract_keyframes_to_dir

log = logging.getLogger(__name__)

STATUS_PROCESSING = "processing"
STATUS_FAILED = "failed"


def run_audio_extraction_job(job_id: int) -> None:
    """
    Этап audio_extraction: WAV; затем frame_analysis: кадры в
    {job_id}/frames; по успеху — transcription.
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

        frames_dir = job_dir / "frames"
        kf_n = extract_keyframes_to_dir(video_path, frames_dir)
        j = db.get(VideoJob, job_id)
        if j is None:
            return
        j.key_frames_count = kf_n
        j.current_stage = STAGE_TRANSCRIPTION
        j.progress_percent = progress_for_stage_id(STAGE_TRANSCRIPTION)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception("Сбой извлечения аудио/кадров job_id=%s", job_id)
        try:
            job = db.get(VideoJob, job_id)
            if job is not None:
                job.last_error = str(exc)[:2000]
                job.status = STATUS_FAILED
                if job.audio_path is None:
                    job.current_stage = STAGE_AUDIO_EXTRACTION
                else:
                    job.current_stage = STAGE_FRAME_ANALYSIS
                db.commit()
        except Exception:  # noqa: BLE001
            log.exception("Не удалось записать ошибку job_id=%s", job_id)
    finally:
        db.close()
