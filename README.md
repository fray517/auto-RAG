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

Пошаговая настройка backend, frontend и Docker — в `plan.md` (этап 0 и далее).

## Лицензия

См. файл `LICENSE`.
