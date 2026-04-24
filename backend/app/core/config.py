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


def get_temp_path() -> Path:
    """
    Каталог временных файлов (TEMP_PATH).

    В Docker: /app/temp, локально: ./temp в корне репозитория, если
    нет `backend/temp`.
    """
    from app.core.env import load_env

    load_env()
    raw = (os.environ.get("TEMP_PATH") or "").strip()
    here = Path(__file__).resolve()
    br = here.parents[2]
    pr = here.parents[3]
    if not raw or raw == "./temp":
        base = br / "temp" if (br / "temp").is_dir() else pr / "temp"
    else:
        p = Path(raw)
        if p.is_absolute():
            base = p
        else:
            rel = raw.lstrip("./")
            base = pr / rel
    out = base.resolve()
    out.mkdir(parents=True, exist_ok=True)
    return out
