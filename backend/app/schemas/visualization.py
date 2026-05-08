"""Схемы API для визуализации учебных материалов."""

from pydantic import BaseModel, Field


class VisualizationCard(BaseModel):
    """Карточка по разделу методички."""

    id: str = Field(description="Стабильный идентификатор карточки")
    title: str = Field(description="Название раздела")
    body: str = Field(description="Краткое содержание раздела")
    sort_order: int = Field(description="Порядок карточки")


class KnowledgeMapNode(BaseModel):
    """Узел простой карты знаний."""

    id: str = Field(description="Идентификатор узла")
    label: str = Field(description="Подпись узла")
    level: int = Field(description="Уровень вложенности")


class KnowledgeMapEdge(BaseModel):
    """Связь между узлами карты знаний."""

    source: str = Field(description="Идентификатор исходного узла")
    target: str = Field(description="Идентификатор целевого узла")


class KnowledgeMap(BaseModel):
    """Граф разделов методички."""

    nodes: list[KnowledgeMapNode] = Field(default_factory=list)
    edges: list[KnowledgeMapEdge] = Field(default_factory=list)


class VisualizationResponse(BaseModel):
    """Данные для страницы визуализации одного материала."""

    job_id: int = Field(description="Идентификатор задачи обработки")
    title: str = Field(description="Название материала")
    cards: list[VisualizationCard] = Field(default_factory=list)
    map: KnowledgeMap = Field(description="Карта знаний")
