"""Схемы API AI-чата."""

from typing import Literal

from pydantic import BaseModel, Field


ChatMode = Literal["strict", "explain"]


class ChatAskRequest(BaseModel):
    """Тело POST /chat/ask."""

    question: str = Field(min_length=1, description="Вопрос пользователя")
    mode: ChatMode = Field(
        default="strict",
        description="Режим ответа: strict или explain",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Сколько фрагментов retrieval использовать",
    )


class ChatSource(BaseModel):
    """Источник ответа из базы знаний."""

    chunk_id: int = Field(description="Идентификатор chunk")
    knowledge_block_id: int = Field(description="Идентификатор блока знаний")
    video_job_id: int = Field(description="Идентификатор video job")
    video_title: str = Field(description="Название видео")
    block_type: str = Field(description="Тип материала")
    section: str | None = Field(description="Раздел материала")
    score: float = Field(description="Cosine similarity")
    excerpt: str = Field(description="Фрагмент текста источника")


class ChatAskResponse(BaseModel):
    """Структурированный ответ AI-чата."""

    answer: str = Field(description="Ответ ассистента")
    mode: ChatMode = Field(description="Режим ответа")
    sources: list[ChatSource] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
