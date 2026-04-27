"""Фоновая задача: аудио, ключевые кадры и транскрибация."""

import logging

from sqlalchemy import delete, select

from app.core.config import get_temp_path
from app.db.session import create_db_session
from app.domain.pipeline_stages import (
    STAGE_AUDIO_EXTRACTION,
    STAGE_FRAME_ANALYSIS,
    STAGE_TRANSCRIPT_CLEANING,
    STAGE_TRANSCRIPTION,
    progress_for_stage_id,
)
from app.models.ocr_result import OcrResult
from app.models.transcripts import RawTranscript
from app.models.video_job import VideoJob
from app.services.audio_ffmpeg import extract_audio_wav, find_input_video
from app.services.keyframes_ffmpeg import extract_keyframes_to_dir
from app.services.ocr_tesseract import extract_text_from_frames
from app.services.openai_stt import transcribe_audio

log = logging.getLogger(__name__)

STATUS_PROCESSING = "processing"
STATUS_FAILED = "failed"


def run_audio_extraction_job(job_id: int) -> None:
    """
    WAV, кадры, OCR в ocr_results и сырой транскрипт в raw_transcripts.
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
        ocr_items = extract_text_from_frames(frames_dir)
        db.execute(
            delete(OcrResult).where(OcrResult.video_job_id == job_id),
        )
        for item in ocr_items:
            db.add(
                OcrResult(
                    video_job_id=job_id,
                    sort_order=item.sort_order,
                    source_hint=item.source_hint,
                    text=item.text,
                ),
            )

        j = db.get(VideoJob, job_id)
        if j is None:
            return
        j.key_frames_count = kf_n
        j.current_stage = STAGE_TRANSCRIPTION
        j.progress_percent = progress_for_stage_id(STAGE_TRANSCRIPTION)
        db.commit()

        transcript_text = transcribe_audio(audio_abs)
        raw = db.execute(
            select(RawTranscript).where(
                RawTranscript.video_job_id == job_id,
            ),
        ).scalar_one_or_none()
        if raw is None:
            raw = RawTranscript(
                video_job_id=job_id,
                content=transcript_text,
            )
            db.add(raw)
        else:
            raw.content = transcript_text

        j = db.get(VideoJob, job_id)
        if j is None:
            return
        j.current_stage = STAGE_TRANSCRIPT_CLEANING
        j.progress_percent = progress_for_stage_id(
            STAGE_TRANSCRIPT_CLEANING,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "Сбой извлечения аудио/кадров/транскрипции job_id=%s",
            job_id,
        )
        try:
            job = db.get(VideoJob, job_id)
            if job is not None:
                job.last_error = str(exc)[:2000]
                job.status = STATUS_FAILED
                if job.current_stage is None:
                    job.current_stage = STAGE_AUDIO_EXTRACTION
                db.commit()
        except Exception:  # noqa: BLE001
            log.exception("Не удалось записать ошибку job_id=%s", job_id)
    finally:
        db.close()
