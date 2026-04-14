# StockNova AI

StockNova AI is a production-ready SaaS-style inventory management platform built with Django, PostgreSQL, Bootstrap 5, HTMX, and Chart.js.

## Highlights

- Professional dashboard with KPI cards and charts
- Full category/product CRUD with image upload
- Smart stock status engine (available/low/out)
- Low stock alerts and visual badges
- Stock movement history and audit log tracking
- Role-based access control with groups and permissions
- Advanced product filtering, sorting, search, pagination
- HTMX instant search interactions
- Export filtered product results to CSV and Excel
- API-ready architecture with DRF endpoints
- Seed command for realistic demo data and credentials
- Celery + Redis asynchronous low-stock notifications
- Docker and docker-compose one-command startup
- CI pipeline for linting, tests, and security checks
- Split settings architecture for dev/prod/ci deployment workflows

## Tech Stack

- Backend: Django 6
- Database: PostgreSQL
- Frontend: Django templates, Bootstrap 5, HTMX, Alpine.js
- Media/Image: Pillow
- Optional APIs: Django REST Framework

## Project Structure

```text
Invexis/
├─ apps/
│  ├─ accounts/
│  └─ inventory/
├─ config/
│  ├─ settings/
│  │  ├─ base.py
│  │  ├─ dev.py
│  │  ├─ prod.py
│  │  └─ ci.py
│  └─ celery.py
├─ docker/
│  └─ entrypoint.sh
├─ .github/workflows/
│  └─ ci.yml
├─ services/
├─ static/
├─ templates/
├─ utils/
├─ manage.py
├─ requirements.txt
├─ .env.example
└─ credentials.md
```

## Setup

1. Create and activate virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and adjust values.
4. Configure PostgreSQL and Redis (or use Docker compose below).
5. Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

6. Seed sample data:

```bash
python manage.py seed_data --categories 8 --products 60
```

7. Start server:

```bash
python manage.py runserver
```

## Celery and Redis

Run worker and scheduler (beat) for asynchronous low-stock checks and alert dispatch:

```bash
celery -A config worker -l info
celery -A config beat -l info
```

Low-stock notifications are triggered asynchronously during product creation/update/stock adjustments and also periodically via Celery beat.

## Docker One-Command Startup

Start app + PostgreSQL + Redis + Celery worker + Celery beat:

```bash
docker compose up --build
```

Application will be available on `http://localhost:8000`.

## Settings Split

- `config.settings.dev`: local development
- `config.settings.prod`: production hardening
- `config.settings.ci`: optimized for CI execution

Set via environment variable:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
```

## CI Pipeline

GitHub Actions workflow at `.github/workflows/ci.yml` runs:

- `ruff` lint
- `bandit` security scan
- `pip-audit` dependency vulnerability scan
- Django migrations and test suite

## Core URLs

- App: `/`
- Dashboard: `/dashboard/`
- Products: `/products/`
- Categories: `/categories/`
- API: `/api/v1/products/`, `/api/v1/categories/`

## Security and Architecture Notes

- CSRF is enabled for all form actions.
- Views use login and permission decorators.
- Product listing uses `select_related` for query optimization.
- Audit and stock movement logs preserve accountability.
- Architecture is app-based and service-oriented for scale.
