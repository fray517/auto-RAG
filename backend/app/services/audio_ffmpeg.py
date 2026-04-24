"""Извлечение аудио из видео через ffmpeg (CLI)."""

import subprocess
from pathlib import Path

_VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm"})


def find_input_video(job_dir: Path) -> Path:
    """Видео, сохранённое как `input.*` при загрузке (шаг 2.1)."""
    cands = sorted(
        p
        for p in job_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in _VIDEO_SUFFIXES
        and p.name.lower().startswith("input")
    )
    if not cands:
        raise FileNotFoundError(
            "Не найден входной видеофайл input.* в каталоге задачи.",
        )
    return cands[0]


def extract_audio_wav(src_video: Path, dst_wav: Path) -> None:
    """
    Моно WAV 16 kHz 16 bit — пригодно для дальнейшей транскрибации.
    """
    dst_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src_video),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(dst_wav),
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
            tail = tail[:500] + "…"
        raise RuntimeError(
            f"ffmpeg завершился с кодом {proc.returncode}: {tail}",
        )
    if not dst_wav.is_file() or dst_wav.stat().st_size == 0:
        raise RuntimeError("audio.wav не создан или пуст.")
