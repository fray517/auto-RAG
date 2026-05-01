"""Генерация конспекта по очищенной транскрипции."""

import base64
import mimetypes
import os
from pathlib import Path

from openai import OpenAI, OpenAIError

from app.core.env import load_env

DEFAULT_SUMMARY_MODEL = "gpt-4.1-mini"
MAX_INPUT_CHARS = 120_000
MAX_SLIDE_IMAGES = 20


def get_summary_model() -> str:
    """Модель LLM для генерации конспекта."""
    load_env()
    model = os.environ.get("OPENAI_SUMMARY_MODEL", "").strip()
    return model or DEFAULT_SUMMARY_MODEL


def _image_data_url(path: Path) -> str:
    media_type, _ = mimetypes.guess_type(path.name)
    media_type = media_type or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _build_user_content(
    clean_text: str,
    slide_image_paths: list[Path],
) -> list[dict[str, object]]:
    content: list[dict[str, object]] = [
        {
            "type": "text",
            "text": (
                "Очищенная транскрипция:\n"
                f"{clean_text.strip()}\n\n"
                "Ниже приложены сохранённые пользователем слайды. "
                "Используй их как визуальный контекст для конспекта: "
                "термины, схемы, графики, подписи и структуру материала.\n\n"
                "Верни только конспект."
            ),
        },
    ]
    for slide_path in slide_image_paths[:MAX_SLIDE_IMAGES]:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": _image_data_url(slide_path),
                    "detail": "low",
                },
            },
        )
    return content


def generate_summary(
    clean_text: str,
    slide_image_paths: list[Path] | None = None,
) -> str:
    """Сформировать учебный конспект по clean transcript и слайдам."""
    load_env()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан.")

    clean_text = clean_text.strip()
    if not clean_text:
        raise RuntimeError("Очищенная транскрипция пуста.")
    if len(clean_text) > MAX_INPUT_CHARS:
        clean_text = clean_text[:MAX_INPUT_CHARS]
    slide_image_paths = slide_image_paths or []

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "Ты методист. Составь структурированный конспект учебного видео "
        "по очищенной транскрипции. Сохрани смысл, порядок объяснения, "
        "ключевые термины и практические выводы. Не добавляй фактов, "
        "которых нет во входных данных. Пиши по-русски. Используй "
        "заголовки, короткие абзацы и списки там, где это помогает."
    )
    try:
        result = client.chat.completions.create(
            model=get_summary_model(),
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": _build_user_content(
                        clean_text,
                        slide_image_paths,
                    ),
                },
            ],
        )
    except OpenAIError as err:
        raise RuntimeError(f"Ошибка OpenAI при генерации конспекта: {err}") \
            from err

    text = result.choices[0].message.content
    summary = (text or "").strip()
    if not summary:
        raise RuntimeError("LLM вернула пустой конспект.")
    return summary
