"""Точка входа FastAPI."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.env import load_env
from app.core.responses import Utf8JSONResponse
from app.db.migrate import run_migrations
from app.routers import videos

load_env()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Миграции до приёма запросов."""
    await asyncio.to_thread(run_migrations)
    yield


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


@app.get("/health")
def health() -> dict[str, str]:
    """Проверка доступности сервиса."""
    return {"status": "ok"}
