# perinatal-contacts-parser

Каталог и API контактов перинатальных центров, женских консультаций, родильных домов, клиник и кафедр акушерства и гинекологии РФ.

**Репозиторий:** https://github.com/EvgeniSasim/perinatal-contacts-parser

## Быстрый старт

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r apps/api/requirements.txt
export PYTHONPATH=apps/api
export ADMIN_API_KEY=dev-admin-key-change-me
export SEED_CSV_PATH=data/seed/institutions.csv
uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

- UI: http://127.0.0.1:8000/
- API: http://127.0.0.1:8000/api/v1/health
- Docs: http://127.0.0.1:8000/docs

Docker (нужен запущенный Docker Desktop):

```bash
COMPOSE_PROJECT_NAME=pnc docker compose up -d --build
```

## Возможности MVP

- 120 seed-записей (все целевые типы учреждений)
- REST: поиск, фильтры, пагинация
- Excel-экспорт по фильтру
- Массовая рассылка (dry-run)
- Admin UI
- WordPress-плагин `[pnc_directory]`

## Документация

- [План](docs/PLAN.md) · [Задачи](docs/TASKS.md) · [Интеграция](docs/INTEGRATION.md)
- [Модель данных](docs/data-model.md) · [Источники](docs/sources-mvp.md)
- [Оркестрация агентов](docs/ORCHESTRATION.md)
