"""Ответы с промежуточными результатами обработки видео."""

from datetime import datetime

from pydantic import BaseModel, Field


class RawTranscriptResponse(BaseModel):
    """Результат GET/PUT /videos/{job_id}/raw-transcript."""

    job_id: int = Field(description="Идентификатор задачи обработки")
    content: str | None = Field(
        default=None,
        description="Сырой текст распознавания речи, если уже готов",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Время последнего сохранения транскрипта",
    )


class RawTranscriptUpdateRequest(BaseModel):
    """Тело PUT /videos/{job_id}/raw-transcript."""

    content: str = Field(description="Обновлённый сырой текст")


class CleanTranscriptResponse(BaseModel):
    """Результат генерации очищенной транскрипции."""

    job_id: int = Field(description="Идентификатор задачи обработки")
    content: str | None = Field(
        default=None,
        description="Очищенная и структурированная транскрипция",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Время последнего сохранения clean transcript",
    )


class CleanTranscriptUpdateRequest(BaseModel):
    """Тело PUT /videos/{job_id}/clean-transcript."""

    content: str = Field(description="Обновлённый очищенный текст")


class SummaryResponse(BaseModel):
    """Конспект по очищенной транскрипции."""

    job_id: int = Field(description="Идентификатор задачи обработки")
    content: str | None = Field(
        default=None,
        description="Сгенерированный конспект",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Время последнего сохранения конспекта",
    )


class MaterialUpdateRequest(BaseModel):
    """Тело PUT для итоговых учебных материалов."""

    content: str = Field(description="Обновлённый текст материала")


class ManualGuideResponse(BaseModel):
    """Методичка по очищенной транскрипции."""

    job_id: int = Field(description="Идентификатор задачи обработки")
    content: str | None = Field(
        default=None,
        description="Сгенерированная методичка",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Время последнего сохранения методички",
    )


class ChecklistResponse(BaseModel):
    """Чек-лист по очищенной транскрипции."""

    job_id: int = Field(description="Идентификатор задачи обработки")
    content: str | None = Field(
        default=None,
        description="Сгенерированный чек-лист",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Время последнего сохранения чек-листа",
    )


class OcrResultItem(BaseModel):
    """Один OCR-результат по ключевому кадру."""

    id: int = Field(description="Идентификатор OCR-записи")
    sort_order: int = Field(description="Порядок кадра в наборе")
    source_hint: str | None = Field(
        default=None,
        description="Имя файла кадра или другой источник",
    )
    text: str | None = Field(
        default=None,
        description="Распознанный текст",
    )


class OcrResultsResponse(BaseModel):
    """Результат GET /videos/{job_id}/ocr."""

    job_id: int = Field(description="Идентификатор задачи обработки")
    items: list[OcrResultItem] = Field(
        default_factory=list,
        description="OCR-результаты в порядке кадров",
    )


class SlideCaptureRequest(BaseModel):
    """Тело POST /videos/{job_id}/slides."""

    timestamp_seconds: float = Field(
        ge=0,
        description="Позиция видео в секундах для сохранения кадра",
    )


class SlideItem(BaseModel):
    """Один вручную выбранный слайд."""

    id: int = Field(description="Идентификатор записи слайда")
    sort_order: int = Field(description="Порядок слайда в задаче")
    source_hint: str = Field(description="Имя файла сохранённого кадра")
    image_url: str = Field(description="URL изображения слайда")


class SlidesResponse(BaseModel):
    """Список вручную выбранных слайдов."""

    job_id: int = Field(description="Идентификатор задачи обработки")
    items: list[SlideItem] = Field(default_factory=list)
