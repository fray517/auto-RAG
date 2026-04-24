# auto-RAG

Локальное веб‑приложение: обучающие видео → транскрипты, материалы, база знаний
и RAG‑чат. Стек и границы MVP описаны в `technical_specification.md`. Порядок
реализации — в `plan.md`.

## Структура репозитория

```text
auto-RAG/
  frontend/     # React (шаг 0.3)
  backend/      # FastAPI (шаг 0.2)
  data/         # БД, постоянные данные приложения
  exports/      # Экспорт (DOCX, PNG)
  temp/         # Временные файлы (видео, аудио, кадры)
  docker/       # Вспомогательные Docker‑файлы
  env.example   # Пример переменных окружения
  docker-compose.yml
  README.md
```

## Переменные окружения

1. Скопируйте `env.example` в `.env` в корне проекта.
2. Заполните значения (см. комментарии в `env.example`).

## Запуск

Пошаговая настройка frontend и детали — в `plan.md` (этап 0 и далее).

**Backend (Docker):** в корне репозитория: `docker compose up --build`, затем
проверка `GET http://localhost:8000/health` (ожидается `{"status":"ok"}`).
Нужен запущенный Docker Desktop (или иной движок) и файл `.env` в корне
(см. `env.example`).

**Backend (локально):** `Set-Location backend; python -m pip install -r requirements.txt; python -m uvicorn app.main:app --reload --port 8000`

## Лицензия

См. файл `LICENSE`.
