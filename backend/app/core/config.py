"""Параметры приложения (чтение из окружения)."""

import os
from pathlib import Path


def _default_db_path() -> Path:
    """
    Каталог data: в Docker — /app/data (том), локально — сосед с backend.

    `backend/app/core/config.py` -> parents[2] = backend, [3] = корень репо.
    """
    here = Path(__file__).resolve()
    backend_root = here.parents[2]
    project_root = here.parents[3]
    if (backend_root / "data").is_dir():
        return (backend_root / "data" / "app.db").resolve()
    return (project_root / "data" / "app.db").resolve()


def get_database_url() -> str:
    """
    URL БД.

    Пустой DATABASE_URL и значение из env.example (sqlite в ./data) —
    в один и тот же физический путь; каталог `data` создаётся при
    необходимости.
    """
    from app.core.env import load_env

    load_env()
    raw = (os.environ.get("DATABASE_URL") or "").strip()
    if not raw or raw == "sqlite:///./data/app.db":
        path = _default_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"
    return raw
