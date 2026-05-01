"""Генерация чек-листа по очищенной транскрипции."""

import base64
import mimetypes
import os
from pathlib import Path

from openai import OpenAI, OpenAIError

from app.core.env import load_env

DEFAULT_CHECKLIST_MODEL = "gpt-4.1-mini"
MAX_INPUT_CHARS = 120_000
MAX_SLIDE_IMAGES = 20


def get_checklist_model() -> str:
    """Модель LLM для генерации чек-листа."""
    load_env()
    model = os.environ.get("OPENAI_CHECKLIST_MODEL", "").strip()
    return model or DEFAULT_CHECKLIST_MODEL


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
                "Используй их как визуальный контекст для терминов, "
                "условий, настроек и практических действий.\n\n"
                "Сформируй отдельный практический чек-лист по материалу. "
                "Пиши пунктами с чекбоксами Markdown вида '- [ ]'. "
                "Сгруппируй пункты по смысловым блокам, если это помогает. "
                "Каждый пункт должен быть проверяемым действием или "
                "критерием. Не добавляй фактов, которых нет во входных "
                "данных.\n\n"
                "Верни только чек-лист."
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


def generate_checklist(
    clean_text: str,
    slide_image_paths: list[Path] | None = None,
) -> str:
    """Сформировать чек-лист по clean transcript и слайдам."""
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
        "Ты методист-практик. Создай полезный чек-лист по учебному видео: "
        "короткие проверяемые пункты, без воды и без фактов вне входных "
        "данных. Пиши по-русски, структурированно и прикладно."
    )
    try:
        result = client.chat.completions.create(
            model=get_checklist_model(),
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
        raise RuntimeError(f"Ошибка OpenAI при генерации чек-листа: {err}") \
            from err

    text = result.choices[0].message.content
    checklist = (text or "").strip()
    if not checklist:
        raise RuntimeError("LLM вернула пустой чек-лист.")
    return checklist
