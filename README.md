<div align="center">

# SalesPipeline

**Комплексная B2B-платформа управления продажами — визуальная воронка, скоринг лидов, прогнозирование выручки, автоматизация outreach и аналитика в реальном времени. Ваш собственный HubSpot / Pipedrive под полным контролем.**

<br/>

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-FF1709?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Channels](https://img.shields.io/badge/Channels-4.2-WebSocket-8A2BE2?style=for-the-badge)](https://channels.readthedocs.io/)
[![Docker](https://img.shields.io/badge/Docker_Compose-3.9-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Nginx](https://img.shields.io/badge/Nginx-Reverse_Proxy-009639?style=for-the-badge&logo=nginx&logoColor=white)](https://nginx.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## Содержание

1. [О проекте](#1-о-проекте)
2. [Ключевые возможности](#2-ключевые-возможности)
3. [Технологический стек](#3-технологический-стек)
4. [Структура репозитория](#4-структура-репозитория)
5. [Архитектура и как это работает](#5-архитектура-и-как-это-работает)
6. [Доменная модель (крупными блоками)](#6-доменная-модель-крупными-блоками)
7. [Сервисы в Docker Compose](#7-сервисы-в-docker-compose)
8. [Быстрый старт (локально, Docker)](#8-быстрый-старт-локально-docker)
9. [Основные команды разработки](#9-основные-команды-разработки)
10. [Ручной запуск frontend и backend](#10-ручной-запуск-frontend-и-backend)
11. [Конфигурация и переменные окружения](#11-конфигурация-и-переменные-окружения)
12. [API, очереди и интеграции](#12-api-очереди-и-интеграции)
13. [WebSocket и real-time](#13-websocket-и-real-time)
14. [Мониторинг и эксплуатация](#14-мониторинг-и-эксплуатация)
15. [Безопасность и роли доступа](#15-безопасность-и-роли-доступа)
16. [Роли компонентов в продакшене](#16-роли-компонентов-в-продакшене)
17. [Лицензия](#17-лицензия)
18. [Поддержка](#18-поддержка)

---

## 1. О проекте

**SalesPipeline** — продуктовая **SaaS-платформа управления продажами** для B2B-команд: от первого касания лида до закрытия сделки и прогноза выручки. Система объединяет Kanban-воронку, автоматический скоринг, многошаговые email-последовательности, взвешенное прогнозирование pipeline и интерактивные дашборды.

Целевая аудитория:

| Аудитория | Что получает |
|-----------|--------------|
| **Менеджеры по продажам** | Kanban-доски, лиды, задачи follow-up, email-секвенции |
| **Руководители отдела** | KPI команды, квоты, прогнозы, отчёты по конверсии |
| **Администраторы** | Управление пользователями, командами, ролями и настройками |
| **Интеграторы** | REST API с JWT, WebSocket для live-обновлений |

Платформа готова к запуску **от локальной разработки до production** через Docker Compose с единой точкой входа Nginx.

### Что это за тип системы

SalesPipeline — **многосервисная распределённая платформа**, а не монолитный скрипт. Бизнес-логика сосредоточена в Django-приложениях, фоновые задачи вынесены в Celery, клиентское приложение — отдельный React SPA.

| Аспект | Описание |
|--------|----------|
| **Продукт** | B2B CRM / Sales Engagement: лиды → сделки → прогноз → отчёты |
| **Архитектура** | Django API + React SPA + Celery workers + Redis + PostgreSQL |
| **Real-time** | Django Channels (WebSocket) через Daphne ASGI |
| **Хранилище** | PostgreSQL (метаданные) + Redis (кэш, сессии, брокер, channel layer) |
| **Деплой** | Docker Compose, Nginx reverse proxy, опционально S3 для медиа |

---

## 2. Ключевые возможности

### Воронка и сделки

- **Визуальный Kanban-pipeline** — настраиваемые этапы с вероятностью закрытия и цветовой кодировкой
- **Drag-and-drop перемещение сделок** между стадиями с полным audit trail (`DealHistory`)
- **Взвешенная стоимость сделки** — `value × stage.probability` для точного pipeline-прогноза
- Несколько pipeline, дефолтный pipeline, привязка лида к сделке

### Лиды и скоринг

- Полный профиль лида: контакты, компания, география, теги, приоритет
- **Автоматический lead scoring** по четырём осям: демография, поведение, вовлечённость, фирмография
- Журнал активностей: звонки, встречи, email, смена статуса, визиты на сайт
- Источники лидов (`LeadSource`) и назначение ответственному менеджеру

### Прогнозирование

- Прогнозы по периодам: месяц / квартал / год
- Сценарии: **predicted**, **best case**, **worst case**, **committed**, **weighted pipeline**
- Разбивка по подпериодам (`ForecastPeriod`) и сравнение с фактом (`accuracy`)
- Область прогноза: pipeline, команда, конкретный sales rep

### Email-секвенции (автоматизация)

- Многошаговые цепочки: email, ожидание, задача, условие
- Персонализация шаблонов (`{{ first_name }}`, `{{ company }}` и др.)
- Трекинг: отправлено / открыто / клик / ответ / bounce
- Celery Beat: периодическая обработка очереди шагов и напоминания follow-up

### Аналитика и отчёты

- Дашборд: выручка, конверсия, активность команды
- Настраиваемые виджеты (`DashboardWidget`): KPI, графики, воронка, leaderboard
- Сохранённые отчёты с расписанием доставки на email (`SavedReport`, `ReportSchedule`)

### Команды и доступ

- Роли: **Admin**, **Manager**, **Sales Rep**, **Viewer**
- Команды продаж (`SalesTeam`) с квотами и профилями (`SalesRep`)
- JWT-аутентификация с ротацией refresh-токенов

### Расширенные модули (в кодовой базе)

- **Каталог продуктов** — категории, SKU, price books, скидки
- **Коммерческие предложения** — квоты с line items, версионирование, статусы (draft → accepted)
- Готовы к подключению через `INSTALLED_APPS` при необходимости

---

## 3. Технологический стек

### Backend

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| Framework | Django 5.1 | ORM, admin, middleware |
| API | Django REST Framework 3.15 | REST endpoints, фильтры, пагинация |
| Auth | djangorestframework-simplejwt 5.3 | JWT access / refresh |
| Async | Django Channels 4.2 + Daphne 4.1 | HTTP + WebSocket (ASGI) |
| Tasks | Celery 5.4 + django-celery-beat | Фоновые задачи и cron |
| Cache | django-redis 5.4 | Кэш и сессии |
| DB driver | psycopg2-binary 2.9 | PostgreSQL |
| Config | django-environ 0.11 | `.env` и `DATABASE_URL` |
| Static | WhiteNoise 6.8 | Сжатые статики в production |
| Quality | black, isort, flake8, pytest | Форматирование и тесты |
| Observability | sentry-sdk 2.19 | Ошибки в production |

### Frontend

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| UI | React 18 | SPA-компоненты |
| State | Redux Toolkit | Глобальное состояние |
| API | Custom hooks + fetch client | Типизированные запросы к REST |
| Auth | JWT в localStorage / hooks | `useAuth`, `useApi` |

### Инфраструктура

| Компонент | Версия | Назначение |
|-----------|--------|------------|
| PostgreSQL | 16 (Alpine) | Основная БД |
| Redis | 7 (Alpine) | Кэш, Celery broker, Channels layer |
| Nginx | Alpine | Reverse proxy, gzip, WebSocket upgrade |
| Docker Compose | 3.9 | Оркестрация всех сервисов |

---

## 4. Структура репозитория

```
SalesPipeline/
├── backend/                          # Django-приложение
│   ├── apps/
│   │   ├── accounts/                 # User, SalesTeam, SalesRep, JWT register
│   │   ├── leads/                    # Lead, LeadScore, LeadActivity, LeadSource
│   │   ├── pipeline/                 # Pipeline, Stage, Deal, DealHistory
│   │   ├── forecasting/              # Forecast, ForecastPeriod
│   │   ├── sequences/                # EmailSequence, Celery tasks
│   │   ├── analytics/                # Dashboard API, агрегации
│   │   ├── products/                 # Каталог, price books (модуль)
│   │   ├── quotations/               # КП и line items (модуль)
│   │   └── reports/                  # SavedReport, ReportSchedule, widgets
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py               # Общие настройки
│   │   │   ├── development.py        # Локальная разработка
│   │   │   └── production.py         # HSTS, Sentry, SSL
│   │   ├── urls.py                   # Маршрутизация API
│   │   ├── asgi.py                   # ASGI + WebSocket consumers
│   │   ├── wsgi.py
│   │   └── celery.py                 # Celery app
│   ├── utils/
│   │   ├── pagination.py             # Стандартная пагинация (25)
│   │   └── exceptions.py             # Единый exception handler
│   ├── requirements.txt
│   ├── Dockerfile
│   └── manage.py
├── frontend/                         # React SPA
│   └── src/
│       ├── api/                      # client.ts, endpoints.ts
│       ├── components/               # auth, layout, leads, pipeline, analytics…
│       ├── pages/                    # Dashboard, Settings
│       ├── store/                    # Redux store
│       ├── hooks/                    # useAuth, useApi
│       └── styles/                   # globals.css
├── nginx/
│   └── nginx.conf                    # Proxy: /api, /ws, /static, /
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 5. Архитектура и как это работает

### Общая схема

```mermaid
flowchart TB
    subgraph Client["Клиент"]
        Browser["Браузер / React SPA"]
    end

    subgraph Edge["Edge"]
        Nginx["Nginx :80/443"]
    end

    subgraph App["Application Layer"]
        Daphne["Daphne ASGI :8000"]
        API["Django REST API"]
        WS["Channels WebSocket"]
    end

    subgraph Workers["Background"]
        CeleryW["Celery Worker"]
        CeleryB["Celery Beat"]
    end

    subgraph Data["Data Layer"]
        PG[("PostgreSQL 16")]
        Redis[("Redis 7")]
    end

    Browser --> Nginx
    Nginx -->|"/api, /admin"| Daphne
    Nginx -->|"/ws"| Daphne
    Nginx -->|"/"| Frontend["React :3000"]
    Daphne --> API
    Daphne --> WS
    API --> PG
    API --> Redis
    WS --> Redis
    CeleryW --> PG
    CeleryW --> Redis
    CeleryB --> CeleryW
```

### Типичный сценарий: сделка перемещена на новый этап

1. Менеджер перетаскивает карточку сделки в React UI.
2. `PATCH /api/pipeline/deals/{id}/move/` обновляет `stage` и пишет запись в `DealHistory`.
3. Backend отправляет событие в Redis Channel Layer → группа `pipeline_{id}`.
4. Все подключённые клиенты по WebSocket `ws/pipeline/{id}/` получают `pipeline.update` без перезагрузки страницы.
5. Celery (при необходимости) пересчитывает взвешенный pipeline для активного прогноза.

### Типичный сценарий: email-секвенция

1. Лид зачисляется в активную секвенцию (`enroll_lead_in_sequence`).
2. Celery Beat каждые N минут вызывает `process_pending_sequence_steps`.
3. Для due-шагов типа `email` ставится задача `send_sequence_email`.
4. Письмо рендерится с контекстом лида, отправляется через SMTP, логируется в `LeadActivity`.
5. Enrollment продвигается к следующему шагу или помечается `completed`.

---

## 6. Доменная модель (крупными блоками)

### Accounts — пользователи и команды

```
User (email, role: admin|manager|sales_rep|viewer)
  └── SalesRep (quota, quota_period, team)
        └── SalesTeam (manager, members)
```

### Leads — привлечение и квалификация

```
LeadSource
  └── Lead (status, priority, assigned_to, estimated_value)
        ├── LeadScore (demographic, behavioral, engagement, firmographic)
        └── LeadActivity (note, email, call, meeting, status_change…)
```

### Pipeline — воронка продаж

```
Pipeline (is_default)
  └── Stage (order, probability, color)
        └── Deal (value, status: open|won|lost, weighted_value)
              └── DealHistory (audit trail)
```

### Forecasting — планирование выручки

```
Forecast (monthly|quarterly|yearly, predicted/best/worst/committed)
  └── ForecastPeriod (sub-period breakdown)
```

### Sequences — outreach-автоматизация

```
EmailSequence (active|paused|draft)
  └── SequenceStep (email|wait|task|condition)
        └── SequenceEnrollment (lead progress, open_rate, click_rate)
```

### Products & Quotations (модули)

```
ProductCategory → Product → PriceBook → PriceBookEntry
QuotationTemplate → Quotation → QuotationLineItem
```

### Reports & Analytics

```
SavedReport → ReportSchedule (email delivery)
DashboardWidget (per-user grid layout)
```

---

## 7. Сервисы в Docker Compose

| Сервис | Образ / сборка | Порт | Назначение |
|--------|----------------|------|------------|
| `db` | `postgres:16-alpine` | 5432 | Основная реляционная БД |
| `redis` | `redis:7-alpine` | 6379 | Кэш, broker, channel layer |
| `backend` | `./backend` Dockerfile | 8000 | Daphne ASGI + migrate on start |
| `celery_worker` | тот же образ | — | Обработка задач (concurrency=4) |
| `celery_beat` | тот же образ | — | Периодические задачи (DB scheduler) |
| `frontend` | `./frontend` Dockerfile | 3000 | React dev/prod server |
| `nginx` | `nginx:alpine` | 80, 443 | Единая точка входа |

**Volumes:** `postgres_data`, `redis_data`, `static_volume`, `media_volume`

**Healthchecks:** PostgreSQL (`pg_isready`), Redis (`PING`) — backend стартует только после готовности зависимостей.

---

## 8. Быстрый старт (локально, Docker)

### Требования

- [Docker](https://docs.docker.com/get-docker/) и Docker Compose v2+
- [Git](https://git-scm.com/)
- 4+ GB RAM для комфортной работы всех контейнеров

### Установка за 5 шагов

```bash
# 1. Клонировать репозиторий
git clone https://github.com/NodirOdilov/SalesPipeline.git
cd SalesPipeline

# 2. Создать файл окружения
cp .env.example .env
# Отредактируйте SECRET_KEY, POSTGRES_PASSWORD, EMAIL_* при необходимости

# 3. Собрать и запустить все сервисы
docker compose up --build -d

# 4. Создать суперпользователя (миграции выполняются при старте backend)
docker compose exec backend python manage.py createsuperuser

# 5. (Опционально) Загрузить демо-данные
docker compose exec backend python manage.py loaddata sample_data
```

### Точки доступа

| Сервис | URL |
|--------|-----|
| **Frontend (React)** | http://localhost:3000 |
| **Backend API** | http://localhost:8000/api/ |
| **Django Admin** | http://localhost:8000/admin/ |
| **Через Nginx** | http://localhost (проксирует всё) |
| **PostgreSQL** | `localhost:5432` |
| **Redis** | `localhost:6379` |

---

## 9. Основные команды разработки

> Makefile в репозитории отсутствует — ниже эквивалентные команды через `docker compose`.

### Docker Compose

```bash
# Запуск в foreground (логи в терминале)
docker compose up

# Запуск в фоне
docker compose up -d

# Пересборка после изменения зависимостей
docker compose up --build

# Остановка
docker compose down

# Остановка с удалением volumes (ОСТОРОЖНО: удалит БД)
docker compose down -v
```

### Django / Backend

```bash
# Миграции
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate

# Django shell
docker compose exec backend python manage.py shell

# Создать суперпользователя
docker compose exec backend python manage.py createsuperuser

# Собрать статику
docker compose exec backend python manage.py collectstatic --noinput
```

### Тесты и качество кода

```bash
# Тесты Django
docker compose exec backend python manage.py test

# Pytest с покрытием
docker compose exec backend pytest --cov=apps

# Форматирование
docker compose exec backend black .
docker compose exec backend isort .
docker compose exec backend flake8 .
```

### Celery

```bash
# Логи worker
docker compose logs -f celery_worker

# Логи beat
docker compose logs -f celery_beat

# Ручной запуск задачи (пример)
docker compose exec backend python manage.py shell -c \
  "from apps.sequences.tasks import process_pending_sequence_steps; process_pending_sequence_steps()"
```

---

## 10. Ручной запуск frontend и backend

Используйте, если нужна отладка без полного Docker-стека (PostgreSQL и Redis всё равно должны быть доступны).

### Backend (локально)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DJANGO_SETTINGS_MODULE=config.settings.development
export DATABASE_URL=postgres://salespipeline:salespipeline_secret@localhost:5432/salespipeline
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/1

python manage.py migrate
python manage.py runserver           # HTTP only (dev)
# или
daphne -b 0.0.0.0 -p 8000 config.asgi:application   # HTTP + WebSocket
```

### Celery (отдельные терминалы)

```bash
celery -A config worker -l info --concurrency=4
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Frontend (локально)

```bash
cd frontend
npm install
export REACT_APP_API_URL=http://localhost:8000/api
export REACT_APP_WS_URL=ws://localhost:8000/ws
npm start                            # http://localhost:3000
```

---

## 11. Конфигурация и переменные окружения

Скопируйте `.env.example` → `.env`. Все переменные читаются через `django-environ`.

### Основные группы

| Группа | Переменные | Описание |
|--------|------------|----------|
| **Django** | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DJANGO_SETTINGS_MODULE` | Базовая безопасность и режим |
| **База данных** | `POSTGRES_*`, `DATABASE_URL` | PostgreSQL connection string |
| **Redis** | `REDIS_URL`, `CELERY_BROKER_URL` | Кэш (db/0), Celery broker (db/1) |
| **JWT** | `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Срок жизни токенов |
| **Email** | `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP для секвенций и напоминаний |
| **Frontend** | `REACT_APP_API_URL`, `REACT_APP_WS_URL` | URL API и WebSocket для SPA |
| **CORS** | `CORS_ALLOWED_ORIGINS` | Разрешённые origins для браузера |
| **Observability** | `SENTRY_DSN` | Sentry (production) |
| **Storage** | `AWS_*` | Опционально S3 для медиа в production |

### Переключение на production

```env
DEBUG=False
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<случайная-строка-минимум-50-символов>
SECURE_SSL_REDIRECT=True
SENTRY_DSN=https://...@sentry.io/...
```

---

## 12. API, очереди и интеграции

### Базовый URL

```
http://localhost:8000/api/
```

Аутентификация: заголовок `Authorization: Bearer <access_token>`.

### Аутентификация

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `POST` | `/api/auth/login/` | Получить JWT access + refresh |
| `POST` | `/api/auth/refresh/` | Обновить access по refresh |
| `POST` | `/api/auth/register/` | Регистрация пользователя |
| `GET/PATCH` | `/api/auth/profile/` | Профиль текущего пользователя |
| `POST` | `/api/auth/change-password/` | Смена пароля |

### Лиды

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET/POST` | `/api/leads/` | Список / создание лидов |
| `GET/PATCH/DELETE` | `/api/leads/{id}/` | CRUD лида |
| `POST` | `/api/leads/{id}/score/` | Пересчёт lead score |
| `GET/POST` | `/api/leads/sources/` | Источники лидов |
| `GET/POST` | `/api/leads/activities/` | Активности |

### Pipeline

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET/POST` | `/api/pipeline/pipelines/` | Воронки |
| `GET/POST` | `/api/pipeline/stages/` | Этапы |
| `GET/POST` | `/api/pipeline/deals/` | Сделки |
| `PATCH` | `/api/pipeline/deals/{id}/move/` | Переместить сделку на этап |

### Прогнозирование

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET/POST` | `/api/forecasting/` | Прогнозы |
| `POST` | `/api/forecasting/{id}/generate/` | Сгенерировать прогноз |

### Секвенции

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET/POST` | `/api/sequences/` | Email-секвенции |
| `POST` | `/api/sequences/{id}/enroll/` | Зачислить лид |

### Аналитика

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/analytics/dashboard/` | Сводка дашборда |
| `GET` | `/api/analytics/performance/` | KPI команды |
| `GET` | `/api/analytics/revenue/` | Аналитика выручки |

### Celery-задачи (фон)

| Задача | Назначение |
|--------|------------|
| `send_sequence_email` | Отправка письма шага секвенции |
| `process_pending_sequence_steps` | Обработка due-шагов (Beat) |
| `send_follow_up_reminders` | Напоминания о просроченных follow-up |
| `enroll_lead_in_sequence` | Асинхронное зачисление лида |

### Ограничения API (throttling)

| Класс | Лимит |
|-------|-------|
| Anonymous | 100 запросов / час |
| Authenticated | 1000 запросов / час |

Пагинация по умолчанию: **25 записей** на страницу.

---

## 13. WebSocket и real-time

### Endpoints

| URL | Consumer | События |
|-----|----------|---------|
| `ws://host/ws/pipeline/{pipeline_id}/` | `PipelineConsumer` | `pipeline.update` — изменения сделок |
| `ws://host/ws/notifications/` | `NotificationConsumer` | Персональные уведомления пользователя |

### Пример подключения (JavaScript)

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/pipeline/default/");

ws.onmessage = (event) => {
  const { type, data } = JSON.parse(event.data);
  if (type === "pipeline.update") {
    // обновить Kanban без перезагрузки
    console.log("Deal moved:", data);
  }
};

ws.send(JSON.stringify({
  type: "pipeline.update",
  data: { deal_id: "...", stage_id: "..." }
}));
```

Nginx проксирует `/ws/` с заголовками `Upgrade` и `Connection: upgrade`.

---

## 14. Мониторинг и эксплуатация

### Логирование

- **Development:** stdout, уровень `INFO` для Django, `DEBUG` для `apps.*`
- **Production:** ротация файла `backend/logs/salespipeline.log` (10 MB × 10 файлов) + stdout

### Sentry (production)

При заданном `SENTRY_DSN` автоматически подключаются интеграции Django и Celery (`traces_sample_rate=0.1`).

### Healthchecks

```bash
# PostgreSQL
docker compose exec db pg_isready -U salespipeline

# Redis
docker compose exec redis redis-cli ping

# Backend (HTTP)
curl -f http://localhost:8000/api/auth/login/ -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test","password":"test"}' || echo "expected 401/400 if alive"
```

### Рекомендации для production

- Используйте managed PostgreSQL и Redis (AWS RDS, ElastiCache, Upstash и т.д.)
- Вынесите `SECRET_KEY` и SMTP-пароли в secrets manager
- Настройте SSL-сертификаты в Nginx (`443`)
- Включите `DEBUG=False` и `config.settings.production`
- Настройте резервное копирование `postgres_data` volume или managed DB snapshots

---

## 15. Безопасность и роли доступа

### Аутентификация

- Email как единственный идентификатор (`AUTH_USER_MODEL = accounts.User`)
- JWT с ротацией refresh-токенов и blacklist после ротации
- Валидаторы паролей Django (длина, сложность, common passwords)

### Роли

| Роль | Возможности |
|------|-------------|
| `admin` | Полный доступ, Django admin |
| `manager` | Команды, прогнозы, аналитика, все сделки команды |
| `sales_rep` | Собственные лиды и сделки, секвенции |
| `viewer` | Только чтение |

### Production hardening (`config.settings.production`)

- `SECURE_SSL_REDIRECT`, HSTS (1 год, preload)
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- `X_FRAME_OPTIONS = DENY`
- `SECURE_PROXY_SSL_HEADER` для работы за Nginx / load balancer

### Файлы и медиа

- Аватары пользователей: `media/avatars/`
- Опционально AWS S3 (`AWS_ACCESS_KEY_ID`, `AWS_STORAGE_BUCKET_NAME`) для production-загрузок

---

## 16. Роли компонентов в продакшене

```
                    ┌─────────────────────────────────────┐
   Internet ───────►│  Load Balancer / CDN (опционально)  │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │           Nginx (TLS termination)    │
                    │  /api, /admin, /ws → backend         │
                    │  /static, /media  → volumes / CDN  │
                    │  /                → frontend build   │
                    └───────┬─────────────────┬───────────┘
                            │                 │
              ┌─────────────▼──────┐   ┌──────▼──────────┐
              │  Daphne × N        │   │  React (static) │
              │  Gunicorn (alt.)   │   │  или SSR CDN    │
              └─────────┬──────────┘   └─────────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
    ┌────▼────┐   ┌─────▼─────┐  ┌────▼─────┐
    │ Celery  │   │ Celery    │  │ Redis    │
    │ Workers │   │ Beat      │  │ Cluster  │
    └────┬────┘   └───────────┘  └────┬─────┘
         │                            │
    ┌────▼────────────────────────────▼────┐
    │         PostgreSQL (primary + replica) │
    └────────────────────────────────────────┘
```

| Компонент | Масштабирование | Заметки |
|-----------|-----------------|---------|
| **Nginx** | Вертикально + несколько инстансов за LB | Terminate TLS, gzip, rate limit |
| **Daphne** | Горизонтально (несколько реплик) | Sticky sessions для WebSocket |
| **Celery Worker** | По длине очереди задач | Отдельные очереди для email vs reports |
| **PostgreSQL** | Read replica для аналитики | Индексы на `deals.status`, `leads.assigned_to` |
| **Redis** | Sentinel / Cluster | Разделить db/0 (cache) и db/1 (broker) |

---

## 17. Лицензия

Проект распространяется под лицензией **MIT**. Подробности — в файле [LICENSE](LICENSE).

Вы можете свободно использовать, модифицировать и распространять код в коммерческих и некоммерческих проектах при сохранении уведомления об авторских правах.

---

## 18. Поддержка

| Канал | Ссылка |
|-------|--------|
| **Issues** | [GitHub Issues](https://github.com/NodirOdilov/SalesPipeline/issues) |
| **Discussions** | [GitHub Discussions](https://github.com/NodirOdilov/SalesPipeline/discussions) |
| **Документация API** | `/admin/` + исходный код `apps/*/views.py` |

При сообщении об ошибке укажите:

1. Версию Docker / ОС
2. Содержимое `.env` **без секретов**
3. Логи: `docker compose logs backend --tail=100`
4. Шаги воспроизведения

---

<div align="center">

**SalesPipeline** — продажи под контролем, данные под рукой, команда в синхроне.

Сделано с ❤️ для команд, которые строят предсказуемую выручку.

</div>
