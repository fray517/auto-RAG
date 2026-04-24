"""Базовый класс моделей ORM."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Метаданные для миграций и моделей."""
