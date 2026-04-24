"""Точка входа FastAPI."""

from fastapi import FastAPI

from app.core.env import load_env

load_env()

app = FastAPI(
    title="auto-RAG API",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Проверка доступности сервиса."""
    return {"status": "ok"}
