"""Маршруты сборки базы знаний."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.responses import Utf8JSONResponse
from app.db.session import get_session
from app.models.knowledge import Chunk, KnowledgeBlock
from app.schemas.knowledge import (
    ChunkItem,
    ChunksResponse,
    EmbeddingsResponse,
    KnowledgeBlockResponse,
    KnowledgePreviewResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.services.chunking import rebuild_chunks_for_block
from app.services.embeddings import (
    rebuild_embeddings_for_block,
    search_chunks,
)
from app.services.knowledge_blocks import (
    MissingMaterialError,
    add_knowledge_block,
    build_knowledge_preview,
)

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    default_response_class=Utf8JSONResponse,
)


def _knowledge_block_response(
    block: KnowledgeBlock,
) -> KnowledgeBlockResponse:
    return KnowledgeBlockResponse(
        id=block.id,
        video_job_id=block.video_job_id,
        video_title=block.video_title,
        summary_text=block.summary_text or "",
        manual_text=block.manual_text or "",
        checklist_text=block.checklist_text or "",
        created_at=block.created_at,
        updated_at=block.updated_at,
    )


def _chunk_item(chunk: Chunk) -> ChunkItem:
    return ChunkItem(
        id=chunk.id,
        knowledge_block_id=chunk.knowledge_block_id,
        block_type=chunk.block_type,
        section=chunk.section,
        body=chunk.body,
        sort_order=chunk.sort_order,
    )


def _get_block_or_404(job_id: int, db: Session) -> KnowledgeBlock:
    block = db.execute(
        select(KnowledgeBlock).where(KnowledgeBlock.video_job_id == job_id),
    ).scalar_one_or_none()
    if block is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge block для этой job ещё не создан.",
        )
    return block


def _missing_material_http_error(err: MissingMaterialError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(err))


def _build_block_or_http_error(
    job_id: int,
    db: Session,
) -> KnowledgeBlock:
    try:
        return add_knowledge_block(job_id, db)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except MissingMaterialError as err:
        raise _missing_material_http_error(err) from err


@router.get(
    "/preview/{job_id}",
    response_model=KnowledgePreviewResponse,
)
def preview_knowledge_block(
    job_id: int,
    db: Session = Depends(get_session),
) -> KnowledgePreviewResponse:
    """Предпросмотр diff перед добавлением блока в базу знаний."""
    try:
        preview = build_knowledge_preview(job_id, db)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except MissingMaterialError as err:
        raise _missing_material_http_error(err) from err
    return KnowledgePreviewResponse(
        video_job_id=preview.draft.video_job_id,
        video_title=preview.draft.video_title,
        current_master_text=preview.current_master_text,
        new_block_text=preview.new_block_text,
        next_master_text=preview.next_master_text,
        diff_text=preview.diff_text,
    )


@router.get(
    "/chunks/{job_id}",
    response_model=ChunksResponse,
)
def get_knowledge_chunks(
    job_id: int,
    db: Session = Depends(get_session),
) -> ChunksResponse:
    """Получить chunks для knowledge block."""
    block = _get_block_or_404(job_id, db)
    chunks = db.execute(
        select(Chunk)
        .where(Chunk.knowledge_block_id == block.id)
        .order_by(Chunk.sort_order, Chunk.id),
    ).scalars()
    return ChunksResponse(
        video_job_id=job_id,
        knowledge_block_id=block.id,
        items=[_chunk_item(chunk) for chunk in chunks],
    )


@router.post(
    "/chunks/{job_id}",
    response_model=ChunksResponse,
)
def rebuild_knowledge_chunks(
    job_id: int,
    db: Session = Depends(get_session),
) -> ChunksResponse:
    """Пересоздать chunks для сохранённого knowledge block."""
    block = _get_block_or_404(job_id, db)
    chunks = rebuild_chunks_for_block(block, db)
    return ChunksResponse(
        video_job_id=job_id,
        knowledge_block_id=block.id,
        items=[_chunk_item(chunk) for chunk in chunks],
    )


@router.post(
    "/embeddings/{job_id}",
    response_model=EmbeddingsResponse,
)
def rebuild_knowledge_embeddings(
    job_id: int,
    db: Session = Depends(get_session),
) -> EmbeddingsResponse:
    """Пересоздать embeddings для chunks knowledge block."""
    block = _get_block_or_404(job_id, db)
    try:
        embeddings = rebuild_embeddings_for_block(block, db)
    except RuntimeError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    first = embeddings[0] if embeddings else None
    return EmbeddingsResponse(
        video_job_id=job_id,
        knowledge_block_id=block.id,
        model_name=first.model_name if first is not None else "",
        vector_dim=first.vector_dim if first is not None else 0,
        embeddings_count=len(embeddings),
    )


@router.post("/search", response_model=SearchResponse)
def search_knowledge(
    payload: SearchRequest,
    db: Session = Depends(get_session),
) -> SearchResponse:
    """Найти top-k релевантных chunks по embeddings."""
    try:
        results = search_chunks(payload.query, db, payload.top_k)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err

    return SearchResponse(
        query=payload.query,
        top_k=payload.top_k,
        items=[
            SearchResultItem(
                chunk_id=result.chunk.id,
                knowledge_block_id=result.block.id,
                video_job_id=result.block.video_job_id,
                video_title=result.block.video_title,
                block_type=result.chunk.block_type,
                section=result.chunk.section,
                body=result.chunk.body,
                score=result.score,
            )
            for result in results
        ],
    )


@router.post(
    "/add/{job_id}",
    response_model=KnowledgeBlockResponse,
)
def add_job_to_knowledge_base(
    job_id: int,
    db: Session = Depends(get_session),
) -> KnowledgeBlockResponse:
    """Подтвердить добавление job в общую базу знаний."""
    block = _build_block_or_http_error(job_id, db)
    return _knowledge_block_response(block)


@router.get(
    "/blocks/{job_id}",
    response_model=KnowledgeBlockResponse,
)
def get_knowledge_block(
    job_id: int,
    db: Session = Depends(get_session),
) -> KnowledgeBlockResponse:
    """Получить собранный knowledge block для job."""
    block = db.execute(
        select(KnowledgeBlock).where(KnowledgeBlock.video_job_id == job_id),
    ).scalar_one_or_none()
    if block is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge block для этой job ещё не создан.",
        )
    return _knowledge_block_response(block)


@router.post(
    "/blocks/{job_id}",
    response_model=KnowledgeBlockResponse,
)
def create_knowledge_block(
    job_id: int,
    db: Session = Depends(get_session),
) -> KnowledgeBlockResponse:
    """Собрать единый knowledge block из итоговых материалов job."""
    block = _build_block_or_http_error(job_id, db)
    return _knowledge_block_response(block)
