"""Точка входа FastAPI."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.env import load_env
from app.core.logging import configure_logging
from app.core.responses import Utf8JSONResponse
from app.db.migrate import run_migrations
from app.routers import chat
from app.routers import knowledge
from app.routers import videos
from app.routers import visualization

load_env()
configure_logging()

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Миграции до приёма запросов."""
    log.info("Запуск auto-RAG API: выполняем миграции.")
    await asyncio.to_thread(run_migrations)
    log.info("auto-RAG API готов к запросам.")
    try:
        yield
    finally:
        log.info("Остановка auto-RAG API.")


app = FastAPI(
    title="auto-RAG API",
    version="0.1.0",
    lifespan=lifespan,
    default_response_class=Utf8JSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(videos.router)
app.include_router(knowledge.router)
app.include_router(chat.router)
app.include_router(visualization.router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> Utf8JSONResponse:
    """Единый формат ожидаемых HTTP-ошибок."""
    if exc.status_code >= 500:
        log.error(
            "HTTP %s на %s %s: %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.detail,
        )
    return Utf8JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "path": request.url.path,
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> Utf8JSONResponse:
    """Читаемый ответ для ошибок входных данных."""
    log.warning(
        "Ошибка валидации на %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return Utf8JSONResponse(
        status_code=422,
        content={
            "detail": "Некорректные данные запроса.",
            "errors": exc.errors(),
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> Utf8JSONResponse:
    """Не отдавать пользователю голый Internal Server Error."""
    log.exception(
        "Неожиданная ошибка на %s %s",
        request.method,
        request.url.path,
    )
    return Utf8JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Внутренняя ошибка сервера. "
                "Подробности записаны в backend-лог."
            ),
            "path": request.url.path,
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Проверка доступности сервиса."""
    return {"status": "ok"}
