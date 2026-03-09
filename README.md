# SalesPipeline - Sales Management & Analytics System

A production-grade sales management platform featuring visual Kanban-style pipeline boards, intelligent lead scoring, AI-powered sales forecasting, team performance tracking, automated email sequences, and real-time analytics.

## Features

- **Visual Pipeline Management**: Drag-and-drop Kanban boards for managing deals across customizable sales stages
- **Lead Scoring**: Automated lead scoring based on engagement, demographics, and behavioral signals
- **Sales Forecasting**: Weighted pipeline forecasting with historical trend analysis
- **Team Performance**: Track individual and team KPIs, quotas, and conversion rates
- **Email Sequences**: Multi-step automated email sequences with enrollment tracking
- **Real-Time Analytics**: Interactive dashboards with revenue charts, conversion funnels, and activity feeds
- **WebSocket Support**: Live updates for pipeline changes and notifications
- **Role-Based Access**: Granular permissions for admins, managers, and sales reps

## Tech Stack

| Layer        | Technology                        |
|-------------|-----------------------------------|
| Backend     | Django 5.x, Django REST Framework |
| Frontend    | React 18, Redux Toolkit           |
| Database    | PostgreSQL 16                     |
| Cache/Queue | Redis 7                           |
| Task Queue  | Celery 5.x                        |
| Real-Time   | Django Channels (WebSocket)       |
| Proxy       | Nginx                             |
| Container   | Docker, Docker Compose            |

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

1. Clone the repository:

```bash
git clone https://github.com/your-org/salespipeline.git
cd salespipeline
```

2. Copy environment variables:

```bash
cp .env.example .env
```

3. Update `.env` with your configuration (database credentials, email settings, secret key).

4. Build and start all services:

```bash
docker-compose up --build
```

5. Run database migrations:

```bash
docker-compose exec backend python manage.py migrate
```

6. Create a superuser:

```bash
docker-compose exec backend python manage.py createsuperuser
```

7. Access the application:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/
- Admin Panel: http://localhost:8000/admin/
- API Documentation: http://localhost:8000/api/docs/

## Project Structure

```
salespipeline/
├── backend/
│   ├── apps/
│   │   ├── accounts/      # User management, teams, sales reps
│   │   ├── leads/          # Lead management and scoring
│   │   ├── pipeline/       # Pipeline, stages, deals
│   │   ├── forecasting/    # Sales forecasting
│   │   ├── sequences/      # Email sequences and automation
│   │   └── analytics/      # Reporting and analytics
│   ├── config/
│   │   ├── settings/       # Environment-specific settings
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   ├── asgi.py
│   │   └── celery.py
│   └── utils/              # Shared utilities
├── frontend/
│   └── src/
│       ├── api/            # API client and service modules
│       ├── components/     # Reusable React components
│       ├── pages/          # Page-level components
│       ├── store/          # Redux store and slices
│       ├── hooks/          # Custom React hooks
│       └── styles/         # Global styles
├── nginx/                  # Nginx configuration
├── docker-compose.yml
└── .env.example
```

## API Endpoints

### Authentication
| Method | Endpoint              | Description        |
|--------|----------------------|--------------------|
| POST   | `/api/auth/login/`    | User login         |
| POST   | `/api/auth/register/` | User registration  |
| POST   | `/api/auth/refresh/`  | Refresh JWT token  |

### Leads
| Method | Endpoint                   | Description          |
|--------|---------------------------|----------------------|
| GET    | `/api/leads/`              | List leads           |
| POST   | `/api/leads/`              | Create lead          |
| GET    | `/api/leads/{id}/`         | Get lead details     |
| PATCH  | `/api/leads/{id}/`         | Update lead          |
| POST   | `/api/leads/{id}/score/`   | Recalculate score    |

### Pipeline
| Method | Endpoint                           | Description        |
|--------|-----------------------------------|--------------------|
| GET    | `/api/pipeline/pipelines/`         | List pipelines     |
| GET    | `/api/pipeline/deals/`             | List deals         |
| PATCH  | `/api/pipeline/deals/{id}/move/`   | Move deal to stage |

### Forecasting
| Method | Endpoint                     | Description          |
|--------|-----------------------------|-----------------------|
| GET    | `/api/forecasting/`          | Get forecast data     |
| POST   | `/api/forecasting/generate/` | Generate new forecast |

### Analytics
| Method | Endpoint                       | Description             |
|--------|-------------------------------|-------------------------|
| GET    | `/api/analytics/dashboard/`    | Dashboard summary       |
| GET    | `/api/analytics/performance/`  | Team performance data   |
| GET    | `/api/analytics/revenue/`      | Revenue analytics       |

## Environment Variables

See `.env.example` for the full list of configuration options.

## Development

### Running Tests

```bash
docker-compose exec backend python manage.py test
```

### Code Formatting

```bash
# Backend
docker-compose exec backend black .
docker-compose exec backend isort .

# Frontend
docker-compose exec frontend npm run lint
```

### Database Management

```bash
# Create new migrations
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate

# Load sample data
docker-compose exec backend python manage.py loaddata sample_data
```

## Deployment

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Set `DJANGO_SETTINGS_MODULE=config.settings.production`
3. Configure a proper `SECRET_KEY`
4. Set up SSL certificates in the Nginx configuration
5. Configure your email provider credentials
6. Use managed PostgreSQL and Redis services

## License

MIT License. See LICENSE for details.
