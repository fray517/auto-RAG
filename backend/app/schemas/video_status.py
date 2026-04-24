"""Ответ GET /videos/{job_id}/status."""

from pydantic import BaseModel, Field


class VideoJobStatusResponse(BaseModel):
    """Состояние задачи обработки видео."""

    job_id: int = Field(description="Идентификатор задачи")
    status: str = Field(description="Код статуса (uploaded, …)")
    stage: str = Field(description="Текущий этап пайплайна")
    progress_percent: int | None = Field(
        default=None,
        description="Процент 0–100, если задан",
        ge=0,
        le=100,
    )
    error: str | None = Field(
        default=None,
        description="Текст ошибки на последнем сбое",
    )
