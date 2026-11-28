# Спутник Самарского университета

Веб-платформа для создания и прохождения интерактивных курсов и тестов для студентов Самарского университета. Пользователи проходят опубликованные курсы с текстовыми, фото- и аудиовопросами, отслеживают историю своих попыток, а авторы и администраторы управляют курсами, статистикой и ролями пользователей.

## Архитектура и стек технологий

Приложение построено по клиент-серверной архитектуре и разворачивается в трёх контейнерах Docker Compose:

```text
Браузер (http://localhost:8080)
        │
        ▼
┌──────────────────────────────┐
│  frontend (Nginx 1.27 + SPA) │  ──► статика React / TypeScript (dist/)
└──────────────┬───────────────┘
               │ проксирование /api/*, /docs, /redoc, /openapi.json
               │ (client_max_body_size 12m)
               ▼
┌──────────────────────────────┐
│   backend (FastAPI / Python) │  ◄──► том media_data (/app/media)
└──────────────┬───────────────┘
               │ SQLAlchemy 2 + Alembic
               ▼
┌──────────────────────────────┐
│      db (PostgreSQL 16)      │  ◄──► том pg_data (/var/lib/postgresql/data)
└──────────────────────────────┘
```

### Технологический стек

- **Frontend:** React 18, TypeScript 5, Vite 6, React Router 6, Nginx 1.27 (multi-stage сборка и reverse proxy).
- **Backend:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2 (синхронный режим), Alembic, Pydantic Settings, PyJWT, bcrypt.
- **База данных:** PostgreSQL 16 с расширением `pg_trgm` для быстрого поиска по подстроке (GIN-индексы). Схема нормализована (3НФ): `users`, `media`, `courses`, `questions`, `answer_options`, `attempts`, `attempt_answers`.
- **Медиахранилище:** бинарные файлы (изображения и аудио) хранятся в Docker-томе `media_data` (`/app/media`), а их метаданные — в таблице `media`. Валидация типа выполняется по сигнатуре (magic bytes).
- **CI:** GitHub Actions (`.github/workflows/ci.yml`) — проверка синтаксиса Python и валидатора медиа, сборка фронтенда (`tsc --noEmit && vite build`) и smoke-тест Docker Compose с проверкой `/api/health`.

### Структура репозитория

```text
Sputnik-Samara/
├── .github/workflows/ci.yml      # GitHub Actions CI
├── backend/
│   ├── app/
│   │   ├── core/                 # Конфиг, БД, JWT, RBAC-зависимости, единый формат ошибок
│   │   ├── media/                # Загрузка/выдача медиа (router.py) и проверка magic bytes (validator.py)
│   │   ├── models/               # SQLAlchemy-модели (user, media, course, attempt)
│   │   ├── routers/              # REST API роутеры (auth, users, courses, questions, attempts)
│   │   ├── main.py               # Точка входа FastAPI, CORS, /api/health
│   │   └── schemas.py            # Pydantic-схемы по контракту OpenAPI
│   ├── docs/                     # Описание схемы БД (db-schema.md) и SQL-запросы статистики (db-queries.sql)
│   ├── migrations/               # Миграции Alembic (0001_initial_schema.py)
│   ├── seed/                     # Идемпотентное заполнение БД и генерация демо-медиа
│   ├── tests/                    # Интеграционные тесты pytest на PostgreSQL
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── requirements.txt
│   └── requirements-dev.txt
├── docs/
│   ├── openapi.yaml              # Единый контракт REST API (OpenAPI 3.0.3)
│   └── schema.sql                # Справочный DDL-дамп начальной миграции
├── frontend/
│   ├── public/                   # Статические ассеты (mascot.png)
│   ├── src/
│   │   ├── api/                  # HTTP-клиент и TypeScript-типы API
│   │   ├── components/           # Layout, Mascot, ProtectedRoute
│   │   ├── context/              # AuthContext (JWT и состояние пользователя)
│   │   └── pages/                # Страницы: главная, каталог, тест, редактор, статистика, админка
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.ts
├── .env.example                  # Шаблон переменных окружения
├── docker-compose.yml            # Оркестрация db, backend и frontend
└── README.md
```

---

## Развёртывание через Docker (одна команда)

Требования: установленные **Docker** и **Docker Compose** (v2).
Создавать файл `.env` **не обязательно** — в `docker-compose.yml` заданы рабочие значения по умолчанию для локального запуска.

```bash
git clone [https://github.com/ZlyGracz/Sputnik-Samara.git](https://github.com/ZlyGracz/Sputnik-Samara.git)
cd Sputnik-Samara
docker compose up --build
```

При запуске контейнер `backend` автоматически и последовательно выполняет:
1. Применение миграций БД (`alembic upgrade head`).
2. Идемпотентную загрузку тестовых аккаунтов, демо-курса «История России» и демо-медиа (`python -m seed.run`).
3. Запуск API-сервера (`uvicorn app.main:app --host 0.0.0.0 --port 8000`).

### Адреса сервисов после запуска

| Сервис | Адрес | Описание |
| :--- | :--- | :--- |
| Веб-приложение (Nginx) | `http://localhost:8080` | Основной интерфейс платформы |
| Swagger UI | `http://localhost:8080/docs` (или `http://localhost:8000/docs`) | Интерактивная документация REST API |
| ReDoc | `http://localhost:8080/redoc` | Альтернативный просмотр API |
| Healthcheck | `http://localhost:8080/api/health` | Проверка доступности API и БД (`{"status":"ok"}`) |
| Backend напрямую | `http://localhost:8000` | Прямой доступ к FastAPI |
| PostgreSQL | `localhost:5433` | Для подключения через DBeaver / pgAdmin (`sputnik` / `sputnik` / `sputnik_dev_password`) |

### Настройка переменных окружения (опционально)

Чтобы изменить доступы к БД, секрет JWT, внешний порт PostgreSQL или отключить автозаполнение сидами:

```bash
cp .env.example .env
```

Основные переменные из `.env.example`:

| Переменная | Значение по умолчанию | Назначение |
| :--- | :--- | :--- |
| `POSTGRES_DB` | `sputnik` | Имя базы данных PostgreSQL |
| `POSTGRES_USER` | `sputnik` | Пользователь БД |
| `POSTGRES_PASSWORD` | `sputnik_dev_password` | Пароль БД (без спецсимволов, подставляется в URL) |
| `DB_HOST_PORT` | `5433` | Порт PostgreSQL на хост-машине |
| `JWT_SECRET` | `dev-only-change-me` | Ключ подписи JWT-токенов (HS256, срок жизни — 24 ч) |
| `SEED_ON_START` | `true` | Загружать ли тестовые данные при старте (`true` / `false`) |

### Управление контейнерами

```bash
# Запуск в фоне
docker compose up -d --build

# Просмотр состояния и логов
docker compose ps
docker compose logs -f backend

# Остановка с сохранением базы данных и медиафайлов
docker compose down

# Полная остановка и удаление томов (сброс БД и загруженных файлов)
docker compose down -v
```

---

## Локальный запуск для разработки (без контейнеризации кода)

Требования: **Python 3.12+**, **Node.js 20+**, запущенный **PostgreSQL 16** (проще всего поднять только БД из Docker Compose).

### 1. Запуск PostgreSQL

```bash
docker compose up -d db
```

### 2. Запуск Backend (порт `8000`)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

export DATABASE_URL="postgresql+psycopg://sputnik:sputnik_dev_password@localhost:5433/sputnik"
alembic upgrade head
python -m seed.run
uvicorn app.main:app --reload --port 8000
```

### 3. Запуск Frontend (порт `5173`)

В отдельном терминале:

```bash
cd frontend
npm install
npm run dev
```

Фронтенд откроется на `http://localhost:5173` (этот origin заранее разрешён в `CORS_ORIGINS` на бэкенде).

### 4. Запуск автотестов Backend

Интеграционные тесты (`backend/tests/test_api.py`) выполняются на реальной базе PostgreSQL `sputnik_test` (порт `5433` из Docker Compose):

```bash
# Один раз создать тестовую БД в запущенном контейнере db
docker compose exec db createdb -U sputnik sputnik_test

# Запустить тесты из папки backend/ (при активированном venv)
cd backend
pytest
```

---

## Роли пользователей и тестовые учётные записи

### Ролевая модель (RBAC)

| Действие | Гость | `user` (Студент) | `creator` (Создатель) | `admin` (Админ) |
| :--- | :---: | :---: | :---: | :---: |
| Регистрация, вход, просмотр каталога опубликованных курсов | да | да | да | да |
| Прохождение курсов, просмотр истории своих попыток и результатов | нет | да | да | да |
| Создание курсов, вопросов и загрузка медиафайлов | нет | нет | да | да |
| Редактирование, публикация и удаление курсов | нет | нет | только свои | любые |
| Просмотр правильных ответов и статистики курса | нет | нет | только свои | любые |
| Список пользователей, смена ролей, блокировка аккаунтов | нет | нет | нет | да |

**Правила изоляции данных:**
- Пользователь видит только собственные попытки (`/api/attempts/*`); чужая попытка возвращает `404` (даже для `admin`).
- Неопубликованный курс (черновик) виден только автору и администратору; остальным возвращается `404`.
- Правильный вариант ответа не отправляется студенту до момента ответа на конкретный вопрос.
- Смена роли и блокировка аккаунта (`is_active = false`) применяются немедленно на уровне БД без перелогина.

### Тестовые учётные записи

Создаются автоматически при первом запуске скриптом `backend/seed/run.py` (данные заданы в `backend/seed/data.py`):

| Роль | Email | Пароль | Отображаемое имя |
| :--- | :--- | :--- | :--- |
| `admin` | `admin@example.com` | `Admin123!` | Администратор |
| `creator` | `creator@example.com` | `Creator123!` | Создатель курсов |
| `user` | `user@example.com` | `User123!` | Студент |

Вместе с учётными записями автоматически создаётся и публикуется демо-курс **«История России»** (автор — `creator@example.com`): 10 вопросов с 4 вариантами ответа, включая 3 вопроса с изображениями и 2 со звуком. По умолчанию используются сгенерированные PNG/WAV-заглушки; чтобы подменить их настоящими файлами, поместите файлы в `backend/seed/assets/<ключ>.<png|jpg|wav|mp3|ogg>` (ключи: `cover`, `monument`, `satellite`, `bell`, `salvo`) и пересоздайте тома (`docker compose down -v && docker compose up --build`).

---

## Загрузка и выдача медиафайлов

- **Загрузка (`POST /api/media`):** доступна ролям `creator` и `admin`, файл передаётся в `multipart/form-data` под ключом `file`.
- **Проверка типа по содержимому (magic bytes) и лимиты:**
  - **Фото:** JPEG, PNG, WebP — до **5 МБ**.
  - **Аудио:** MP3, OGG, WAV — до **10 МБ**.
  - При неподдерживаемом типе (включая подмену расширения) возвращается `415`, при превышении лимита — `413`.
- **Выдача (`GET /api/media/{media_id}`):** публичный эндпоинт без токена (для работы тегов `<img>` и `<audio>`), возвращает бинарный файл с корректным `Content-Type` и относительной ссылкой вида `/api/media/{uuid}`.

---

## Примеры основных запросов к API (`curl`)

Все пути указаны через Nginx (`http://localhost:8080`), без слешей в конце URL. Ошибки API возвращаются в едином формате `{"detail": "текст ошибки на русском"}`.

### 1. Проверка работоспособности

```bash
curl http://localhost:8080/api/health
```

### 2. Регистрация нового пользователя (`user`)

```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"Str0ngPass!","full_name":"Иван Петров"}'
```

### 3. Вход (JSON) и сохранение JWT-токена

```bash
# Вход под создателем курсов (для студента используйте user@example.com / User123!, для админа — admin@example.com / Admin123!)
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"creator@example.com","password":"Creator123!"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "$TOKEN"
```

### 4. Получение профиля текущего пользователя

```bash
curl http://localhost:8080/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Каталог опубликованных курсов (публичный)

```bash
curl "http://localhost:8080/api/courses?search=История&limit=20&offset=0"
```

### 6. Загрузка и получение медиафайла (`creator`, `admin`)

```bash
# Загрузка изображения или аудио (в ответе придут id и относительный url вида /api/media/{uuid})
curl -X POST http://localhost:8080/api/media \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./example.jpg"

# Публичное скачивание файла по UUID (без токена)
curl -o downloaded.jpg http://localhost:8080/api/media/<media_id>
```

### 7. Создание курса, добавление вопроса и публикация (`creator`, `admin`)

```bash
# Создать черновик курса
curl -X POST http://localhost:8080/api/courses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Основы Linux","description":"Команды терминала и права доступа"}'

# Добавить вопрос с 4 вариантами (ровно один правильный) в курс с id=2
curl -X POST http://localhost:8080/api/courses/2/questions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Какая команда показывает текущую директорию?",
    "options": [
      {"text": "cd", "is_correct": false},
      {"text": "pwd", "is_correct": true},
      {"text": "ls", "is_correct": false},
      {"text": "mkdir", "is_correct": false}
    ]
  }'

# Опубликовать курс
curl -X PATCH http://localhost:8080/api/courses/2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_published":true}'
```

### 8. Прохождение курса и просмотр своих попыток (любой авторизованный пользователь)

```bash
# Начать попытку по опубликованному курсу с id=1 (возвращает AttemptDetail с вопросами и option_id)
curl -X POST http://localhost:8080/api/courses/1/attempts \
  -H "Authorization: Bearer $TOKEN"

# Ответить на вопрос в рамках попытки (подставьте реальные attempt_id, question_id и option_id)
curl -X POST http://localhost:8080/api/attempts/1/answers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question_id":1,"option_id":2}'

# Завершить попытку и получить итоговый балл и процент
curl -X POST http://localhost:8080/api/attempts/1/finish \
  -H "Authorization: Bearer $TOKEN"

# История своих попыток
curl http://localhost:8080/api/attempts/my \
  -H "Authorization: Bearer $TOKEN"
```

### 9. Статистика курса (`creator` — свои курсы, `admin` — любые)

```bash
curl http://localhost:8080/api/courses/1/stats \
  -H "Authorization: Bearer $TOKEN"
```

### 10. Управление пользователями (`admin`)

```bash
# Список пользователей с фильтрацией по роли
curl "http://localhost:8080/api/users?role=user&limit=20&offset=0" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Выдать пользователю роль creator или заблокировать аккаунт
curl -X PATCH http://localhost:8080/api/users/3 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role":"creator","is_active":true}'
```

---

## Дополнительная документация

- Контракт REST API: [`docs/openapi.yaml`](docs/openapi.yaml)
- Схема базы данных и ER-диаграмма: [`backend/docs/db-schema.md`](backend/docs/db-schema.md)
- SQL-дамп начальной миграции: [`docs/schema.sql`](docs/schema.sql)
- Справочные SQL-запросы для результатов и статистики: [`backend/docs/db-queries.sql`](backend/docs/db-queries.sql)