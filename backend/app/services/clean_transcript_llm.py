"""Очистка сырой транскрипции через LLM."""

import os

from openai import OpenAI, OpenAIError

from app.core.env import load_env

DEFAULT_CLEAN_MODEL = "gpt-4.1-mini"
MAX_INPUT_CHARS = 120_000


def get_clean_transcript_model() -> str:
    """Модель LLM для очистки транскрипции."""
    load_env()
    model = os.environ.get("OPENAI_CLEAN_TRANSCRIPT_MODEL", "").strip()
    return model or DEFAULT_CLEAN_MODEL


def _build_user_prompt(raw_text: str, ocr_text: str) -> str:
    ocr_block = ocr_text.strip() or "OCR-текста нет."
    return (
        "Сырая транскрипция:\n"
        f"{raw_text.strip()}\n\n"
        "OCR/текст со слайдов, если есть:\n"
        f"{ocr_block}\n\n"
        "Верни только очищенную транскрипцию."
    )


def clean_transcript(raw_text: str, ocr_text: str = "") -> str:
    """
    Убрать воду и слова-паразиты, сохранив смысл лекции.

    OCR используется как дополнительный контекст, но не должен заменять речь.
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
                    "content": _build_user_prompt(raw_text, ocr_text),
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
