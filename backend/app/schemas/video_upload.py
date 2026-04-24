"""Ответ при загрузке видео."""

from pydantic import BaseModel, Field


class VideoUploadResponse(BaseModel):
    """Результат POST /videos/upload."""

    job_id: int = Field(description="Идентификатор задачи обработки")
    status: str = Field(description="Статус задачи")
    filename: str = Field(description="Имя файла, как у клиента")
    stored_path: str = Field(
        description="Относительный путь сохранённого файла в TEMP_PATH",
    )
