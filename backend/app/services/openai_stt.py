"""Транскрибация аудио через OpenAI."""

import os
import shutil
import subprocess
from pathlib import Path

from openai import OpenAI, OpenAIError

from app.core.env import load_env

DEFAULT_TRANSCRIPTION_MODEL = "whisper-1"
DEFAULT_CHUNK_SECONDS = 600
MAX_OPENAI_AUDIO_BYTES = 24_000_000


def get_transcription_model() -> str:
    """Имя модели STT из окружения или стабильное значение по умолчанию."""
    load_env()
    model = os.environ.get("OPENAI_TRANSCRIPTION_MODEL", "")
    return model.strip() or DEFAULT_TRANSCRIPTION_MODEL


def get_stt_chunk_seconds() -> int:
    """Длительность одного STT-чанка в секундах."""
    load_env()
    raw = os.environ.get("OPENAI_STT_CHUNK_SECONDS", "")
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_CHUNK_SECONDS
    if value < 60:
        return DEFAULT_CHUNK_SECONDS
    return value


def _transcribe_single_file(
    client: OpenAI,
    model: str,
    audio_path: Path,
) -> str:
    try:
        with audio_path.open("rb") as audio_file:
            result = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                response_format="text",
            )
    except OpenAIError as err:
        raise RuntimeError(f"Ошибка OpenAI STT: {err}") from err

    if isinstance(result, str):
        text = result
    else:
        text = getattr(result, "text", "")
    text = text.strip()
    if not text:
        raise RuntimeError("OpenAI STT вернул пустую транскрипцию.")
    return text


def _split_audio_to_chunks(audio_path: Path, chunks_dir: Path) -> list[Path]:
    shutil.rmtree(chunks_dir, ignore_errors=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    pattern = chunks_dir / "chunk_%03d.wav"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(audio_path),
        "-f",
        "segment",
        "-segment_time",
        str(get_stt_chunk_seconds()),
        "-c",
        "copy",
        str(pattern),
    ]
    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()
        if len(tail) > 500:
            tail = tail[:500] + "..."
        raise RuntimeError(
            f"ffmpeg не смог разделить аудио на STT-чанки: {tail}",
        )

    chunks = sorted(chunks_dir.glob("chunk_*.wav"))
    chunks = [p for p in chunks if p.is_file() and p.stat().st_size > 0]
    if not chunks:
        raise RuntimeError("ffmpeg не создал STT-чанки.")
    too_large = [
        p.name
        for p in chunks
        if p.stat().st_size > MAX_OPENAI_AUDIO_BYTES
    ]
    if too_large:
        raise RuntimeError(
            "STT-чанк всё ещё больше лимита OpenAI: "
            f"{', '.join(too_large)}. Уменьшите OPENAI_STT_CHUNK_SECONDS.",
        )
    return chunks


def transcribe_audio(audio_path: Path) -> str:
    """Отправить аудиофайл в OpenAI STT и вернуть распознанный текст."""
    load_env()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан.")
    if not audio_path.is_file() or audio_path.stat().st_size == 0:
        raise FileNotFoundError("Аудиофайл для транскрибации не найден.")

    client = OpenAI(api_key=api_key)
    model = get_transcription_model()

    if audio_path.stat().st_size <= MAX_OPENAI_AUDIO_BYTES:
        return _transcribe_single_file(client, model, audio_path)

    chunks_dir = audio_path.parent / "stt_chunks"
    try:
        chunks = _split_audio_to_chunks(audio_path, chunks_dir)
        parts = [
            _transcribe_single_file(client, model, chunk)
            for chunk in chunks
        ]
        text = "\n\n".join(part for part in parts if part.strip()).strip()
        if not text:
            raise RuntimeError("OpenAI STT вернул пустую транскрипцию.")
        return text
    finally:
        shutil.rmtree(chunks_dir, ignore_errors=True)
