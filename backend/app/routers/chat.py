"""Маршруты AI-чата."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.responses import Utf8JSONResponse
from app.db.session import get_session
from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.services.chat_llm import ask_chat

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    default_response_class=Utf8JSONResponse,
)


@router.post("/ask", response_model=ChatAskResponse)
def ask(
    payload: ChatAskRequest,
    db: Session = Depends(get_session),
) -> ChatAskResponse:
    """Ответить на вопрос по базе знаний."""
    try:
        result = ask_chat(
            question=payload.question,
            mode=payload.mode,
            top_k=payload.top_k,
            db=db,
        )
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except RuntimeError as err:
        raise HTTPException(status_code=500, detail=str(err)) from err

    return ChatAskResponse(
        answer=result.answer,
        mode=payload.mode,
        sources=result.sources,
        sections=result.sections,
    )
