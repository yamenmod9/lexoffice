# LexOffice Backend (Flask)

Production-oriented Flask REST API for LexOffice (Legal Office Management SaaS) with tenant isolation for Egyptian law firms.

## Stack

- Python 3.11
- Flask 3.x + factory pattern
- SQLAlchemy + Flask-Migrate (Alembic)
- PostgreSQL primary database
- Redis for OTP/session cache and Celery broker/backends
- Celery + Beat for background jobs
- Flask-JWT-Extended (access + refresh)
- Marshmallow validation
- Flask-Limiter, Flask-CORS
- Flask-Mail, Twilio, Firebase, Azure OpenAI, S3/Local storage

## Folder Structure

- app/config.py: environment configuration
- app/extensions.py: Flask extension singletons
- app/models/: complete schema entities and enums
- app/api/: versioned API modules
- app/services/: integrations and business services
- app/tasks/: Celery app + scheduled jobs
- app/utils/: shared response/error/security/audit helpers
- seed/seed_data.py: seed default templates and courts metadata check
- tests/: pytest suite

## Setup

1. Create virtual environment and install dependencies:

```bash
pip install --no-cache-dir -r requirements.txt
```

2. Configure environment variables:

```bash
copy .env.example .env
```

3. Run migrations:

```bash
flask --app run.py db init
flask --app run.py db migrate -m "initial schema"
flask --app run.py db upgrade
```

4. Start API:

```bash
python run.py
```

5. Start Celery worker:

```bash
celery -A celery_worker.celery worker -B --loglevel=info
```

6. Seed default templates:

```bash
python seed/seed_data.py
```

## Security Defaults

- Password policy enforced (min 8 with uppercase, number, symbol)
- JWT access 1 hour / refresh 30 days
- Login and OTP verification rate limited
- Rate limiter uses Redis when available and automatically falls back to in-memory storage if Redis is unavailable
- Office-based tenant filtering at query level
- CSRF header check on authenticated state-changing requests (`X-CSRF-Token`)
- Write-operation audit logging enabled globally

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## PythonAnywhere Notes

- If your account has limited disk quota, always install with `--no-cache-dir`.
- The default `requirements.txt` is runtime-focused to reduce deployment size.
- Optional integrations (Firebase push + dev/test tools) are in `requirements-dev.txt`.

## Endpoint Tester Page

After starting the backend server, open:

```text
http://localhost:5000/endpoint-tester
```

The page includes one button to run automated checks against all registered Flask endpoints.
