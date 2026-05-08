"""Маршруты визуализации материалов."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.responses import Utf8JSONResponse
from app.db.session import get_session
from app.models.materials import ManualGuide
from app.models.video_job import VideoJob
from app.schemas.visualization import (
    KnowledgeMap,
    KnowledgeMapEdge,
    KnowledgeMapNode,
    VisualizationCard,
    VisualizationResponse,
)
from app.services.visualization_builder import build_visualization_data

router = APIRouter(
    prefix="/visualization",
    tags=["visualization"],
    default_response_class=Utf8JSONResponse,
)


@router.get("/{job_id}", response_model=VisualizationResponse)
def get_visualization(
    job_id: int,
    db: Session = Depends(get_session),
) -> VisualizationResponse:
    """Построить карточки и карту знаний по методичке job."""
    job = db.get(VideoJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    manual = db.execute(
        select(ManualGuide).where(ManualGuide.video_job_id == job_id),
    ).scalar_one_or_none()
    if manual is None or not (manual.content or "").strip():
        raise HTTPException(
            status_code=409,
            detail="Методичка ещё не создана.",
        )

    try:
        data = build_visualization_data(job, manual)
    except ValueError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    cards = [
        VisualizationCard(
            id=section.id,
            title=section.title,
            body=section.body,
            sort_order=section.sort_order,
        )
        for section in data.sections
    ]
    nodes = [
        KnowledgeMapNode(
            id=section.id,
            label=section.title,
            level=section.level,
        )
        for section in data.sections
    ]
    edges = [
        KnowledgeMapEdge(source=section.parent_id, target=section.id)
        for section in data.sections
        if section.parent_id is not None
    ]
    return VisualizationResponse(
        job_id=data.job_id,
        title=data.title,
        cards=cards,
        map=KnowledgeMap(nodes=nodes, edges=edges),
    )
