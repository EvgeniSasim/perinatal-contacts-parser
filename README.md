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

- Реальные источники: OSM, OrgPage, MedAdvisor, КП, Zdrav.expert, RussiaMedTravel, Vademecum, PDF Минздрава
- 2GIS / Яндекс API (по ключам)
- ~480 учреждений в seed
- REST: поиск, фильтры, пагинация
- Excel-экспорт, mailing dry-run, Admin UI, WP-плагин

Сбор каталогов:

```bash
PYTHONPATH=apps/api python scripts/crawl_real.py --source catalogs
```

## Документация

- [План](docs/PLAN.md) · [Задачи](docs/TASKS.md) · [Интеграция](docs/INTEGRATION.md)
- [Модель данных](docs/data-model.md) · [Источники](docs/sources-mvp.md)
- [Оркестрация агентов](docs/ORCHESTRATION.md)
