"""Схемы API для базы знаний."""

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBlockResponse(BaseModel):
    """Единый блок знаний, собранный из результатов video job."""

    id: int = Field(description="Идентификатор knowledge block")
    video_job_id: int = Field(description="Идентификатор задачи обработки")
    video_title: str = Field(description="Название видео")
    summary_text: str = Field(description="Конспект")
    manual_text: str = Field(description="Методичка")
    checklist_text: str = Field(description="Чек-лист")
    created_at: datetime = Field(description="Время создания блока")
    updated_at: datetime = Field(description="Время последнего обновления")


class KnowledgePreviewResponse(BaseModel):
    """Предпросмотр добавления блока в master-представление БЗ."""

    video_job_id: int = Field(description="Идентификатор задачи обработки")
    video_title: str = Field(description="Название видео")
    current_master_text: str = Field(
        description="Текущее master-представление без нового блока",
    )
    new_block_text: str = Field(
        description="Текст блока, который будет добавлен",
    )
    next_master_text: str = Field(
        description="Master-представление после добавления блока",
    )
    diff_text: str = Field(
        description="Unified diff между текущим и будущим master",
    )


class ChunkItem(BaseModel):
    """Один chunk knowledge block."""

    id: int = Field(description="Идентификатор chunk")
    knowledge_block_id: int = Field(description="Идентификатор блока знаний")
    block_type: str = Field(description="Тип блока: summary/manual/checklist")
    section: str | None = Field(description="Раздел внутри материала")
    body: str = Field(description="Текст chunk")
    sort_order: int = Field(description="Порядок chunk внутри блока")


class ChunksResponse(BaseModel):
    """Список chunks для knowledge block."""

    video_job_id: int = Field(description="Идентификатор задачи обработки")
    knowledge_block_id: int = Field(description="Идентификатор блока знаний")
    items: list[ChunkItem] = Field(default_factory=list)


class EmbeddingsResponse(BaseModel):
    """Результат генерации embeddings для блока."""

    video_job_id: int = Field(description="Идентификатор задачи обработки")
    knowledge_block_id: int = Field(description="Идентификатор блока знаний")
    model_name: str = Field(description="Модель embeddings")
    vector_dim: int = Field(description="Размерность вектора")
    embeddings_count: int = Field(description="Количество embeddings")


class SearchRequest(BaseModel):
    """Тело запроса семантического поиска."""

    query: str = Field(min_length=1, description="Вопрос или поисковая фраза")
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Сколько релевантных chunks вернуть",
    )


class SearchResultItem(BaseModel):
    """Один найденный chunk."""

    chunk_id: int = Field(description="Идентификатор chunk")
    knowledge_block_id: int = Field(description="Идентификатор блока знаний")
    video_job_id: int = Field(description="Идентификатор video job")
    video_title: str = Field(description="Название видео")
    block_type: str = Field(description="Тип блока")
    section: str | None = Field(description="Раздел")
    body: str = Field(description="Текст найденного chunk")
    score: float = Field(description="Cosine similarity")


class SearchResponse(BaseModel):
    """Ответ retrieval по embeddings."""

    query: str = Field(description="Исходный запрос")
    top_k: int = Field(description="Запрошенное число результатов")
    items: list[SearchResultItem] = Field(default_factory=list)
