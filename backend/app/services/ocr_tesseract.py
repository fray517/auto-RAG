"""OCR по ключевым кадрам через локальный Tesseract."""

import os
from dataclasses import dataclass
from pathlib import Path

import pytesseract
from pytesseract import TesseractError, TesseractNotFoundError

from app.core.env import load_env

DEFAULT_OCR_LANG = "rus+eng"
_IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png"})


@dataclass(frozen=True)
class FrameOcrText:
    """Результат OCR для одного кадра."""

    sort_order: int
    source_hint: str
    text: str


def get_ocr_lang() -> str:
    """Языки Tesseract из окружения или русский+английский по умолчанию."""
    load_env()
    lang = os.environ.get("OCR_LANG", "")
    return lang.strip() or DEFAULT_OCR_LANG


def _iter_frame_paths(frames_dir: Path) -> list[Path]:
    if not frames_dir.is_dir():
        raise FileNotFoundError("Каталог ключевых кадров не найден.")
    return sorted(
        p
        for p in frames_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
    )


def _normalize_ocr_text(raw_text: str) -> str:
    lines = (line.strip() for line in raw_text.splitlines())
    return "\n".join(line for line in lines if line).strip()


def extract_text_from_frames(frames_dir: Path) -> list[FrameOcrText]:
    """Распознать текст на ключевых кадрах и вернуть непустые результаты."""
    frames = _iter_frame_paths(frames_dir)
    if not frames:
        raise RuntimeError("Нет кадров для OCR.")

    lang = get_ocr_lang()
    results: list[FrameOcrText] = []
    for sort_order, frame_path in enumerate(frames):
        try:
            raw_text = pytesseract.image_to_string(
                str(frame_path),
                lang=lang,
            )
        except TesseractNotFoundError as err:
            raise RuntimeError("Tesseract OCR не установлен.") from err
        except TesseractError as err:
            raise RuntimeError(
                f"Ошибка Tesseract OCR для {frame_path.name}: {err}",
            ) from err

        text = _normalize_ocr_text(raw_text)
        if text:
            results.append(
                FrameOcrText(
                    sort_order=sort_order,
                    source_hint=frame_path.name,
                    text=text,
                ),
            )
    return results
