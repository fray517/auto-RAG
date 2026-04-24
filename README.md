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

Пошаговые детали — в `plan.md` (этап 0 и далее).

**Всё в Docker (backend + frontend):** в корне:
`docker compose up --build`. UI: `http://localhost:3000` (статус API на
главной), API: `http://localhost:8000/health`. В `.env` должен быть
`VITE_API_BASE_URL` (см. `env.example`).

**Только backend (локально):**
`Set-Location backend; python -m pip install -r requirements.txt; python -m uvicorn app.main:app --reload --port 8000`

**Только frontend (dev, порт 3000):** в корневом `.env` — `VITE_API_BASE_URL`
и запуск:
`Set-Location frontend; npm install; npm run dev`
(без Docker backend на `http://localhost:8000` статус на главной покажет
«недоступен»).

## Лицензия

См. файл `LICENSE`.
