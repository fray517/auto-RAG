"""Фабрика движка и сессий SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_database_url


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


_engine = None
_SessionLocal = None


def get_engine():
    """Ленивый singleton движка (для тестов и API позже)."""
    global _engine, _SessionLocal
    if _engine is None:
        url = get_database_url()
        _engine = create_engine(url, connect_args=_connect_args(url))
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine,
        )
    return _engine


def get_session() -> Generator[Session, None, None]:
    """Зависимость FastAPI: одна сессия на запрос (шаги 1.2+)."""
    get_engine()
    if _SessionLocal is None:
        raise RuntimeError("Session factory is not initialized")
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_db_session() -> Session:
    """Сессия для фоновых задач; закрывать вручную в finally."""
    get_engine()
    if _SessionLocal is None:
        raise RuntimeError("Session factory is not initialized")
    return _SessionLocal()
