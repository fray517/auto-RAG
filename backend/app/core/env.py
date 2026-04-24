"""Загрузка переменных окружения из .env в корне репозитория."""

from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    """Подгрузить .env: на хосте — корень репо, в образе — каталог backend."""
    here = Path(__file__).resolve()
    # Сначала корень монорепозитория, затем каталог backend (Docker).
    for root in (here.parents[3], here.parents[2]):
        candidate = root / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            return
