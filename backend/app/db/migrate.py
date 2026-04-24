"""Запуск Alembic upgrade head (старт приложения)."""

from pathlib import Path

from alembic import command
from alembic.config import Config


def run_migrations() -> None:
    """Применить все неприменённые миграции."""
    backend_root = Path(__file__).resolve().parents[2]
    ini_path = backend_root / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    command.upgrade(alembic_cfg, "head")
