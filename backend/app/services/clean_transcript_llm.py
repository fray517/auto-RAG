"""Очистка сырой транскрипции через LLM."""

import base64
import mimetypes
import os
from pathlib import Path

from openai import OpenAI, OpenAIError

from app.core.env import load_env

DEFAULT_CLEAN_MODEL = "gpt-4.1-mini"
MAX_INPUT_CHARS = 120_000
MAX_SLIDE_IMAGES = 20


def get_clean_transcript_model() -> str:
    """Модель LLM для очистки транскрипции."""
    load_env()
    model = os.environ.get("OPENAI_CLEAN_TRANSCRIPT_MODEL", "").strip()
    return model or DEFAULT_CLEAN_MODEL


def _image_data_url(path: Path) -> str:
    media_type, _ = mimetypes.guess_type(path.name)
    media_type = media_type or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def _build_user_content(
    raw_text: str,
    slide_image_paths: list[Path],
) -> list[dict[str, object]]:
    content: list[dict[str, object]] = [
        {
            "type": "text",
            "text": (
                "Сырая транскрипция:\n"
                f"{raw_text.strip()}\n\n"
                "Ниже приложены сохранённые пользователем слайды. "
                "Используй их как визуальный контекст для терминов, "
                "структуры и примеров, но не заменяй ими речь.\n\n"
                "Верни только очищенную транскрипцию."
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


def clean_transcript(
    raw_text: str,
    slide_image_paths: list[Path] | None = None,
) -> str:
    """
    Убрать воду и слова-паразиты, сохранив смысл лекции.

    Сохранённые слайды используются как визуальный контекст.
    """
    load_env()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан.")

    raw_text = raw_text.strip()
    if not raw_text:
        raise RuntimeError("Сырая транскрипция пуста.")
    if len(raw_text) > MAX_INPUT_CHARS:
        raw_text = raw_text[:MAX_INPUT_CHARS]
    slide_image_paths = slide_image_paths or []

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "Ты редактор учебных транскриптов. Очисти расшифровку лекции: "
        "убери слова-паразиты, повторы, оговорки и технический мусор; "
        "структурируй хаотичную речь в понятные абзацы; сохрани термины, "
        "имена, примеры и порядок мыслей. Не добавляй фактов, которых нет "
        "во входных данных. Пиши по-русски."
    )
    try:
        result = client.chat.completions.create(
            model=get_clean_transcript_model(),
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": _build_user_content(
                        raw_text,
                        slide_image_paths,
                    ),
                },
            ],
        )
    except OpenAIError as err:
        raise RuntimeError(f"Ошибка OpenAI при очистке транскрипции: {err}") \
            from err

    text = result.choices[0].message.content
    cleaned = (text or "").strip()
    if not cleaned:
        raise RuntimeError("LLM вернула пустую очищенную транскрипцию.")
    return cleaned
