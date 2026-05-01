"""AI-чат поверх retrieval из базы знаний."""

import os
from dataclasses import dataclass

from openai import OpenAI, OpenAIError
from sqlalchemy.orm import Session

from app.core.env import load_env
from app.schemas.chat import ChatMode, ChatSource
from app.services.embeddings import SearchResult, search_chunks

DEFAULT_CHAT_MODEL = "gpt-4.1-mini"
MIN_STRICT_SCORE = 0.25
MAX_CONTEXT_CHARS = 12_000
EXCERPT_CHARS = 500


@dataclass(frozen=True)
class ChatResult:
    """Ответ чата вместе с источниками."""

    answer: str
    sources: list[ChatSource]
    sections: list[str]


def get_chat_model() -> str:
    """Модель LLM для AI-чата."""
    load_env()
    model = os.environ.get("OPENAI_CHAT_MODEL", "").strip()
    return model or DEFAULT_CHAT_MODEL


def _get_client() -> OpenAI:
    load_env()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан.")
    return OpenAI(api_key=api_key)


def _source_excerpt(text: str) -> str:
    text = " ".join(text.strip().split())
    if len(text) <= EXCERPT_CHARS:
        return text
    return f"{text[:EXCERPT_CHARS].rstrip()}..."


def _sources_from_results(results: list[SearchResult]) -> list[ChatSource]:
    return [
        ChatSource(
            chunk_id=result.chunk.id,
            knowledge_block_id=result.block.id,
            video_job_id=result.block.video_job_id,
            video_title=result.block.video_title,
            block_type=result.chunk.block_type,
            section=result.chunk.section,
            score=result.score,
            excerpt=_source_excerpt(result.chunk.body),
        )
        for result in results
    ]


def _sections_from_sources(sources: list[ChatSource]) -> list[str]:
    seen: set[str] = set()
    sections: list[str] = []
    for source in sources:
        parts = [source.video_title, source.block_type]
        if source.section:
            parts.append(source.section)
        label = " / ".join(parts)
        if label not in seen:
            seen.add(label)
            sections.append(label)
    return sections


def _context_from_results(results: list[SearchResult]) -> str:
    parts: list[str] = []
    total = 0
    for index, result in enumerate(results, start=1):
        section = result.chunk.section or "Без раздела"
        part = (
            f"[Источник {index}]\n"
            f"video_job_id: {result.block.video_job_id}\n"
            f"video_title: {result.block.video_title}\n"
            f"block_type: {result.chunk.block_type}\n"
            f"section: {section}\n"
            f"score: {result.score:.4f}\n"
            f"text:\n{result.chunk.body.strip()}"
        )
        if total + len(part) > MAX_CONTEXT_CHARS:
            break
        parts.append(part)
        total += len(part)
    return "\n\n---\n\n".join(parts)


def _system_prompt(mode: ChatMode) -> str:
    if mode == "strict":
        return (
            "Ты отвечаешь строго по предоставленным фрагментам базы знаний. "
            "Не используй внешние знания и не додумывай. Если во фрагментах "
            "нет достаточной информации, честно скажи, что в базе знаний "
            "нет ответа. Пиши по-русски. В конце кратко укажи, какие "
            "источники использовал."
        )
    return (
        "Ты помогаешь разобраться в учебном материале по найденным "
        "фрагментам базы знаний. Можно объяснять понятнее и связывать идеи, "
        "но нельзя добавлять факты, которые противоречат источникам или "
        "не опираются на них. Пиши по-русски. В конце кратко укажи, какие "
        "источники использовал."
    )


def _low_context_answer() -> str:
    return (
        "В базе знаний недостаточно релевантного контекста, чтобы ответить "
        "строго по документу без домысливания."
    )


def ask_chat(
    question: str,
    mode: ChatMode,
    top_k: int,
    db: Session,
) -> ChatResult:
    """Ответить на вопрос через retrieval + LLM."""
    question = question.strip()
    if not question:
        raise ValueError("Вопрос пуст.")

    results = search_chunks(question, db, top_k)
    sources = _sources_from_results(results)
    sections = _sections_from_sources(sources)

    best_score = results[0].score if results else 0.0
    if mode == "strict" and best_score < MIN_STRICT_SCORE:
        return ChatResult(
            answer=_low_context_answer(),
            sources=sources,
            sections=sections,
        )

    context = _context_from_results(results)
    if not context:
        return ChatResult(
            answer=_low_context_answer(),
            sources=[],
            sections=[],
        )

    client = _get_client()
    user_prompt = (
        f"Вопрос пользователя:\n{question}\n\n"
        f"Найденный контекст:\n{context}\n\n"
        "Сформируй ответ и не теряй связь с источниками."
    )
    try:
        response = client.chat.completions.create(
            model=get_chat_model(),
            temperature=0.1 if mode == "strict" else 0.35,
            messages=[
                {"role": "system", "content": _system_prompt(mode)},
                {"role": "user", "content": user_prompt},
            ],
        )
    except OpenAIError as err:
        raise RuntimeError(f"Ошибка OpenAI при ответе чата: {err}") from err

    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("LLM вернула пустой ответ.")
    return ChatResult(answer=answer, sources=sources, sections=sections)
