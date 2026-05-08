"""Схемы API для удаления данных video job."""

from pydantic import BaseModel, Field


class VideoJobDeleteResponse(BaseModel):
    """Итог удаления job и связанных данных."""

    job_id: int = Field(description="Идентификатор удалённой job")
    deleted_records: dict[str, int] = Field(
        description="Количество удалённых записей по таблицам",
    )
    deleted_files: list[str] = Field(
        default_factory=list,
        description="Удалённые служебные пути",
    )
