"""Embeddings и retrieval для chunks базы знаний."""

import json
import math
import os
from dataclasses import dataclass

from openai import OpenAI, OpenAIError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.env import load_env
from app.models.knowledge import Chunk, Embedding, KnowledgeBlock

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_TOP_K = 5
MAX_TOP_K = 20


@dataclass(frozen=True)
class SearchResult:
    """Результат поиска по embeddings."""

    chunk: Chunk
    block: KnowledgeBlock
    score: float


def get_embedding_model() -> str:
    """Модель OpenAI для embeddings."""
    load_env()
    model = os.environ.get("OPENAI_EMBEDDING_MODEL", "").strip()
    return model or DEFAULT_EMBEDDING_MODEL


def _get_client() -> OpenAI:
    load_env()
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан.")
    return OpenAI(api_key=api_key)


def _embedding_input(chunk: Chunk) -> str:
    section = (chunk.section or "").strip()
    prefix = f"{chunk.block_type}"
    if section:
        prefix = f"{prefix}: {section}"
    return f"{prefix}\n\n{chunk.body.strip()}"


def _embed_texts(texts: list[str], model: str) -> list[list[float]]:
    if not texts:
        return []
    client = _get_client()
    try:
        result = client.embeddings.create(
            model=model,
            input=texts,
        )
    except OpenAIError as err:
        raise RuntimeError(f"Ошибка OpenAI при embeddings: {err}") from err
    return [list(item.embedding) for item in result.data]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def rebuild_embeddings_for_block(
    block: KnowledgeBlock,
    db: Session,
) -> list[Embedding]:
    """Пересоздать embeddings для всех chunks блока."""
    chunks = list(
        db.execute(
            select(Chunk)
            .where(Chunk.knowledge_block_id == block.id)
            .order_by(Chunk.sort_order, Chunk.id),
        ).scalars(),
    )
    if not chunks:
        raise RuntimeError("Для knowledge block нет chunks.")

    model = get_embedding_model()
    vectors = _embed_texts([_embedding_input(chunk) for chunk in chunks], model)
    embeddings: list[Embedding] = []

    for chunk, vector in zip(chunks, vectors):
        embedding = db.execute(
            select(Embedding).where(Embedding.chunk_id == chunk.id),
        ).scalar_one_or_none()
        if embedding is None:
            embedding = Embedding(chunk_id=chunk.id)
            db.add(embedding)
        embedding.model_name = model
        embedding.vector_dim = len(vector)
        embedding.vector_json = json.dumps(vector, separators=(",", ":"))
        embeddings.append(embedding)

    db.commit()
    for embedding in embeddings:
        db.refresh(embedding)
    return embeddings


def search_chunks(
    query: str,
    db: Session,
    top_k: int = DEFAULT_TOP_K,
) -> list[SearchResult]:
    """Найти top-k релевантных chunks по embedding запроса."""
    query = query.strip()
    if not query:
        raise ValueError("Поисковый запрос пуст.")

    top_k = max(1, min(top_k, MAX_TOP_K))
    model = get_embedding_model()
    query_vector = _embed_texts([query], model)[0]

    rows = db.execute(
        select(Chunk, Embedding, KnowledgeBlock)
        .join(Embedding, Embedding.chunk_id == Chunk.id)
        .join(KnowledgeBlock, KnowledgeBlock.id == Chunk.knowledge_block_id)
        .where(Embedding.model_name == model),
    ).all()

    scored: list[SearchResult] = []
    for chunk, embedding, block in rows:
        try:
            vector = json.loads(embedding.vector_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(vector, list):
            continue
        score = _cosine_similarity(query_vector, [float(x) for x in vector])
        scored.append(SearchResult(chunk=chunk, block=block, score=score))

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_k]
