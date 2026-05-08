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

## Установка

**Через Docker (рекомендуется):** установите [Docker Desktop](https://www.docker.com/products/docker-desktop/) для Windows. Клонировать репозиторий, перейти в корень проекта в PowerShell.

**Без Docker — для разработки:** Python 3.11+ и Node.js 20+ (LTS). Пакеты: backend — `requirements.txt`, frontend — `npm install` в каталоге `frontend`.

## Переменные окружения

1. Скопируйте `env.example` в `.env` в корне проекта:
   `Copy-Item -Path .\env.example -Destination .\.env`
2. Заполните значения по комментариям в `env.example`. Обязательно:
   - `OPENAI_API_KEY` — для LLM и встроенных AI‑шагов;
   - `VITE_API_BASE_URL` — URL API для браузера (в Docker по умолчанию `http://localhost:8005`).
3. Дополнительно: `LOG_LEVEL` (уровень логов backend, по умолчанию `INFO`).

Docker Compose подхватывает `.env` из корня; при изменении переменных после
подъёма контейнеров пересоздайте сервисы (см. ниже).

## Запуск через Docker

В корне проекта:

```powershell
docker compose up --build
```

- UI: `http://localhost:3000`
- API: `http://localhost:8005`, проверка: `http://localhost:8005/health`

После правок кода образов пересоберите и пересоздайте контейнеры:

```powershell
docker compose build
docker compose up -d --force-recreate
```

Логи backend смотрите в выводе сервиса `backend` или через `docker compose logs
-f backend`.

## Запуск без Docker

**Backend:**

```powershell
Set-Location backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
```

**Frontend (dev, порт 3000):** в корневом `.env` задайте `VITE_API_BASE_URL`
(например `http://localhost:8005`), затем:

```powershell
Set-Location frontend
npm install
npm run dev
```

Если backend не запущен, на главной будет статус «недоступен».

## Порядок использования (UI)

1. **Главная** — проверка доступности API.
2. **Загрузка** — выбор видео, создание задачи (job); при необходимости кадры
   слайдов.
3. **Обработка** — отслеживание пайплайна, этапа и ошибок при сбое.
4. **Транскрипт** — правка сырого и очищенного текста.
5. **Материалы** — конспект, методичка, чек‑лист и связанные действия.
6. **Визуализация / база знаний** — блок знаний, дифф, поиск по chunks.
7. **Чат** — RAG‑ответы с источниками.

Подробности этапов — в `plan.md`.

## Типовой сценарий проверки (smoke)

1. Поднять стек (`docker compose up --build` или локально backend + frontend).
2. Убедиться в `GET /health` (200).
3. Загрузить короткое тестовое видео, дождаться завершения или явного сбоя на
   странице обработки (этап и текст ошибки должны быть понятны).
4. Открыть транскрипт и материалы, убедиться, что данные подтягиваются.
5. При изменении `.env` или Dockerfile — пересборка и `--force-recreate`, как
   выше.

Пошаговые детали и критерии шагов — в `plan.md`.

## Лицензия

См. файл `LICENSE`.
