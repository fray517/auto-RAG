"""Генерация основной методички по очищенной транскрипции."""

import base64
import mimetypes
import os
from pathlib import Path

from openai import OpenAI, OpenAIError

from app.core.env import load_env

DEFAULT_MANUAL_GUIDE_MODEL = "gpt-4.1-mini"
MAX_INPUT_CHARS = 120_000
MAX_SLIDE_IMAGES = 20


def get_manual_guide_model() -> str:
    """Модель LLM для генерации методички."""
    load_env()
    model = os.environ.get("OPENAI_MANUAL_GUIDE_MODEL", "").strip()
    return model or DEFAULT_MANUAL_GUIDE_MODEL


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
                "Используй их как визуальный контекст для структуры, "
                "примеров, терминов, схем и пошаговых инструкций.\n\n"
                "Сформируй методичку со строгой структурой. "
                "Используй названия разделов ниже дословно:\n"
                "1. Заголовок\n"
                "2. Краткое содержание\n"
                "3. Основные разделы\n"
                "4. Пошаговые инструкции\n"
                "5. Тезисы\n"
                "6. Примеры\n"
                "7. Чек-листы\n"
                "8. FAQ\n"
                "9. Выводы\n\n"
                "Верни только текст методички."
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


def generate_manual_guide(
    clean_text: str,
    slide_image_paths: list[Path] | None = None,
) -> str:
    """Сформировать основной учебный документ по clean transcript."""
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
        "Ты методист и технический редактор. Создай подробную методичку "
        "по учебному видео. Не добавляй фактов, которых нет во входных "
        "данных. Сохраняй порядок объяснения, термины, примеры и "
        "практические выводы. Пиши по-русски, ясно и структурированно."
    )
    try:
        result = client.chat.completions.create(
            model=get_manual_guide_model(),
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
        raise RuntimeError(f"Ошибка OpenAI при генерации методички: {err}") \
            from err

    text = result.choices[0].message.content
    manual = (text or "").strip()
    if not manual:
        raise RuntimeError("LLM вернула пустую методичку.")
    return manual
