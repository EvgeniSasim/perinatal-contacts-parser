# Handoff: Coder → Reviewer

## Что сделано

- FastAPI `/api/v1` public + admin (API key)
- PostgreSQL через Docker Compose (+ SQLite для pytest)
- Seed CSV 120 записей, автозагрузка на startup
- HTML collector с allowlist (anti-SSRF) + fixture
- Excel export (openpyxl), mailing dry-run
- Admin UI на `/` (static)
- WP plugin `apps/wp-plugin/perinatal-contacts`
- CI workflow, tests (7 passed locally)

## Запуск

```bash
docker compose up -d --build
# UI http://localhost:8000/
# API http://localhost:8000/api/v1/health
# Admin key: ADMIN_API_KEY / default dev-admin-key-change-me
```

Локально без Docker:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r apps/api/requirements.txt
export PYTHONPATH=apps/api ADMIN_API_KEY=test-key SEED_CSV_PATH=data/seed/institutions.csv
uvicorn app.main:app --reload --app-dir apps/api
```

## Известные пробелы

- Celery/Redis worker не используется (sync jobs)
- Отдельный Next.js не выделен — admin в API static
- Live SMTP не реализован (намеренно)
- Alembic миграции не добавлены (create_all)
- `on_event("startup")` deprecated warning
