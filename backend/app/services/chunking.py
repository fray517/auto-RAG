"""Чанкинг knowledge block по markdown-разделам."""

import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.knowledge import Chunk, Embedding, KnowledgeBlock

MAX_CHUNK_CHARS = 2_400
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class ChunkDraft:
    """Подготовленный chunk перед записью в БД."""

    block_type: str
    section: str
    body: str
    sort_order: int


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _split_long_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    parts: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        candidate = f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            parts.append(current)
            current = paragraph
    if current:
        parts.append(current)

    result: list[str] = []
    for part in parts:
        if len(part) <= max_chars:
            result.append(part)
            continue
        for start in range(0, len(part), max_chars):
            result.append(part[start:start + max_chars].strip())
    return [part for part in result if part]


def _split_markdown_sections(
    text: str,
    fallback_section: str,
) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = fallback_section
    current_lines: list[str] = []

    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match and current_lines:
            sections.append((current_title, current_lines))
            current_title = match.group(2).strip()
            current_lines = [line]
        elif match:
            current_title = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    result: list[tuple[str, str]] = []
    for title, lines in sections:
        body = "\n".join(lines).strip()
        if body:
            result.append((title, body))
    return result


def make_chunk_drafts(block: KnowledgeBlock) -> list[ChunkDraft]:
    """Разбить сохранённый knowledge block на логические chunks."""
    sources = [
        ("summary", "Конспект", block.summary_text),
        ("manual", "Методичка", block.manual_text),
        ("checklist", "Чек-лист", block.checklist_text),
    ]
    drafts: list[ChunkDraft] = []
    sort_order = 0

    for block_type, fallback_section, text in sources:
        for section, body in _split_markdown_sections(
            _clean_text(text),
            fallback_section,
        ):
            parts = _split_long_text(body)
            for index, part in enumerate(parts, start=1):
                label = section
                if len(parts) > 1:
                    label = f"{section} — часть {index}"
                drafts.append(
                    ChunkDraft(
                        block_type=block_type,
                        section=label,
                        body=part,
                        sort_order=sort_order,
                    ),
                )
                sort_order += 1

    return drafts


def rebuild_chunks_for_block(
    block: KnowledgeBlock,
    db: Session,
) -> list[Chunk]:
    """Пересоздать chunks для блока и удалить устаревшие embeddings."""
    existing_ids = list(
        db.execute(
            select(Chunk.id).where(Chunk.knowledge_block_id == block.id),
        ).scalars(),
    )
    if existing_ids:
        db.execute(delete(Embedding).where(Embedding.chunk_id.in_(existing_ids)))
        db.execute(delete(Chunk).where(Chunk.id.in_(existing_ids)))

    chunks: list[Chunk] = []
    for draft in make_chunk_drafts(block):
        chunk = Chunk(
            knowledge_block_id=block.id,
            block_type=draft.block_type,
            section=draft.section,
            body=draft.body,
            sort_order=draft.sort_order,
        )
        chunks.append(chunk)
        db.add(chunk)

    db.commit()
    for chunk in chunks:
        db.refresh(chunk)
    return chunks
