"""Построение карточек и простой карты знаний из методички."""

import re
from dataclasses import dataclass
from pathlib import Path

from app.models.materials import ManualGuide
from app.models.video_job import VideoJob


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:[.)])?\s+(.+?)\s*$")
_MAX_CARD_BODY = 420


@dataclass(frozen=True)
class VisualizationSection:
    """Раздел методички для визуального представления."""

    id: str
    title: str
    body: str
    level: int
    sort_order: int
    parent_id: str | None


@dataclass(frozen=True)
class VisualizationData:
    """Полные данные визуализации одного материала."""

    job_id: int
    title: str
    sections: list[VisualizationSection]


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _video_title(filename: str) -> str:
    title = Path(filename).stem.strip()
    return title or filename.strip() or "Без названия"


def _shorten_body(text: str) -> str:
    compact = re.sub(r"\s+", " ", _clean_text(text))
    if len(compact) <= _MAX_CARD_BODY:
        return compact
    return f"{compact[: _MAX_CARD_BODY - 1].rstrip()}..."


def _plain_title(line: str) -> tuple[int, str] | None:
    md_match = _HEADING_RE.match(line)
    if md_match is not None:
        return len(md_match.group(1)), md_match.group(2).strip()

    numbered_match = _NUMBERED_HEADING_RE.match(line)
    if numbered_match is not None:
        number = numbered_match.group(1)
        level = min(number.count(".") + 1, 6)
        title = f"{number} {numbered_match.group(2).strip()}"
        return level, title

    return None


def _fallback_sections(manual_text: str) -> list[VisualizationSection]:
    paragraphs = [
        part.strip()
        for part in re.split(r"\n\s*\n", manual_text)
        if part.strip()
    ]
    sections: list[VisualizationSection] = []
    for index, paragraph in enumerate(paragraphs[:12]):
        first_line = paragraph.splitlines()[0].strip()
        title = first_line[:80] or f"Раздел {index + 1}"
        sections.append(
            VisualizationSection(
                id=f"section-{index + 1}",
                title=title,
                body=_shorten_body(paragraph),
                level=1,
                sort_order=index,
                parent_id=None,
            ),
        )
    return sections


def build_visualization_data(
    job: VideoJob,
    manual: ManualGuide,
) -> VisualizationData:
    """Собрать карточки и иерархию разделов по тексту методички."""
    manual_text = _clean_text(manual.content)
    if not manual_text:
        raise ValueError("Методичка пуста.")

    sections: list[VisualizationSection] = []
    current_title: str | None = None
    current_level = 1
    current_body: list[str] = []
    level_stack: dict[int, str] = {}

    def flush_section() -> None:
        nonlocal current_body, current_level, current_title
        if current_title is None:
            return
        index = len(sections)
        section_id = f"section-{index + 1}"
        parent_id = None
        for level in range(current_level - 1, 0, -1):
            if level in level_stack:
                parent_id = level_stack[level]
                break
        sections.append(
            VisualizationSection(
                id=section_id,
                title=current_title,
                body=_shorten_body("\n".join(current_body)),
                level=current_level,
                sort_order=index,
                parent_id=parent_id,
            ),
        )
        level_stack[current_level] = section_id
        for level in list(level_stack):
            if level > current_level:
                del level_stack[level]
        current_title = None
        current_body = []

    for raw_line in manual_text.splitlines():
        line = raw_line.strip()
        heading = _plain_title(line)
        if heading is not None:
            flush_section()
            current_level, current_title = heading
            current_body = []
            continue
        if current_title is not None:
            current_body.append(raw_line)

    flush_section()

    if not sections:
        sections = _fallback_sections(manual_text)

    return VisualizationData(
        job_id=job.id,
        title=_video_title(job.filename),
        sections=sections,
    )
