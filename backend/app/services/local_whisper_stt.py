"""Локальная транскрибация через faster-whisper."""

import logging
import os
import re
import threading
from functools import lru_cache
from pathlib import Path

from app.core.env import load_env

DEFAULT_LOCAL_STT_MODEL = "large-v3"
DEFAULT_LOCAL_STT_DEVICE = "cuda"
DEFAULT_LOCAL_STT_COMPUTE_TYPE = "float16"
DEFAULT_LOCAL_STT_VAD_FILTER = True
DEFAULT_LOCAL_STT_MIN_SILENCE_MS = 700

log = logging.getLogger(__name__)
_STT_LOCK = threading.Lock()
_SUBTITLE_CREDIT_RE = re.compile(
    r"(?i)\b(субтитр|subtitle).{0,80}\b("
    r"созда|добав|dimatorzok|torzok"
    r")",
)


def _env_value(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on", "да"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw)
    except ValueError:
        return default


def get_local_stt_model_name() -> str:
    """Имя локальной модели Whisper."""
    load_env()
    return _env_value("LOCAL_STT_MODEL", DEFAULT_LOCAL_STT_MODEL)


def get_local_stt_device() -> str:
    """Устройство inference: cuda для RTX или cpu для запасного режима."""
    load_env()
    return _env_value("LOCAL_STT_DEVICE", DEFAULT_LOCAL_STT_DEVICE)


def get_local_stt_compute_type() -> str:
    """Тип вычислений faster-whisper."""
    load_env()
    return _env_value(
        "LOCAL_STT_COMPUTE_TYPE",
        DEFAULT_LOCAL_STT_COMPUTE_TYPE,
    )


def get_local_stt_language() -> str | None:
    """Язык транскрибации или None для автоопределения."""
    load_env()
    value = os.environ.get("LOCAL_STT_LANGUAGE", "").strip()
    return value or None


def get_local_stt_vad_filter() -> bool:
    """Включить VAD, чтобы Whisper не распознавал тишину как текст."""
    load_env()
    return _env_bool("LOCAL_STT_VAD_FILTER", DEFAULT_LOCAL_STT_VAD_FILTER)


def get_local_stt_min_silence_ms() -> int:
    """Минимальная пауза для VAD в миллисекундах."""
    load_env()
    return _env_int(
        "LOCAL_STT_MIN_SILENCE_MS",
        DEFAULT_LOCAL_STT_MIN_SILENCE_MS,
    )


def clean_transcription_text(parts: list[str]) -> str:
    """Убрать типичные hallucination-строки faster-whisper на тишине."""
    cleaned: list[str] = []
    seen_counts: dict[str, int] = {}

    for part in parts:
        line = " ".join(part.split()).strip()
        if not line:
            continue
        normalized = line.casefold()
        if _SUBTITLE_CREDIT_RE.search(normalized):
            log.info("STT filter: удалена строка субтитров: %s", line)
            continue

        seen_counts[normalized] = seen_counts.get(normalized, 0) + 1
        if seen_counts[normalized] > 2 and len(line) <= 120:
            log.info("STT filter: удалён повтор hallucination: %s", line)
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()


@lru_cache(maxsize=4)
def _get_model(model_name: str, device: str, compute_type: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as err:
        raise RuntimeError(
            "Пакет faster-whisper не установлен. "
            "Установите зависимости backend из requirements.txt.",
        ) from err

    log.info(
        "Загрузка локальной STT-модели: model=%s device=%s compute=%s",
        model_name,
        device,
        compute_type,
    )
    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )


def transcribe_audio(audio_path: Path) -> str:
    """Распознать речь локально и вернуть сырой текст."""
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise FileNotFoundError("Аудиофайл для транскрибации не найден.")

    model_name = get_local_stt_model_name()
    device = get_local_stt_device()
    compute_type = get_local_stt_compute_type()
    language = get_local_stt_language()
    vad_filter = get_local_stt_vad_filter()
    min_silence_ms = get_local_stt_min_silence_ms()
    log.info(
        "Ожидание очереди STT: file=%s model=%s device=%s",
        audio_path.name,
        model_name,
        device,
    )
    with _STT_LOCK:
        log.info("Начата локальная STT: file=%s", audio_path)
        model = _get_model(model_name, device, compute_type)
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            language=language,
            vad_filter=vad_filter,
            vad_parameters={"min_silence_duration_ms": min_silence_ms},
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
        )

        parts: list[str] = []
        for index, segment in enumerate(segments, start=1):
            text_part = segment.text.strip()
            if text_part:
                parts.append(text_part)
            if index % 20 == 0:
                log.info(
                    "STT обработала сегментов: %s, позиция %.1f сек.",
                    index,
                    segment.end,
                )

    text = clean_transcription_text(parts)
    if not text:
        raise RuntimeError("Локальная STT вернула пустую транскрипцию.")
    log.info(
        "Локальная STT завершена: язык=%s, символов=%s",
        getattr(info, "language", None),
        len(text),
    )
    return text
