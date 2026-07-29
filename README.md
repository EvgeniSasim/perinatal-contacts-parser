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

## Возможности

- Реальные источники: OSM, OrgPage, MedAdvisor, КП, Zdrav.expert, RussiaMedTravel, Vademecum, PDF Минздрава
- 2GIS / Яндекс API (по ключам)
- 482 учреждения в seed
- Обогащение ФИО руководства и email с официальных сайтов учреждений
- REST: поиск, фильтры, пагинация, персоны с уровнем достоверности
- Excel-экспорт (2 листа), рассылка с подстановкой ФИО, Admin UI, WP-плагин

```bash
# сбор каталогов
PYTHONPATH=apps/api python3 scripts/crawl_real.py --source catalogs

# обогащение ФИО и email
python3 scripts/enrich.py --limit 100 --with-site-only --verbose
python3 scripts/enrich.py --report          # только метрики
```

## Статус данных

| Поле | v0.1 | v0.2 | Цель v0.2 |
|------|------|------|-----------|
| Адрес | 96% | 96% | 98% |
| Телефон | 44% | 44% | 75% |
| Email | 2% | **8%** | 60% |
| ФИО главного врача | 0% | **5%** (23 записи) | 60% |
| Зав. отделением патологии | 0% | **3%** (12) | 25% |
| Персон с должностями | 0 | **624** | — |

Цели не достигнуты, и причина не в извлечении, а в исходных данных: **сайт известен лишь
у 100 из 482 учреждений, и лишь около трети этих доменов отвечает.** На доступных сайтах
конвейер работает — точность ФИО 95% на выборке, 6/6 на калибровочном наборе.

Поиск сайтов через OpenStreetMap проверен на 150 записях и дал **0 результатов**: в OSM у
этих учреждений просто нет тега `website`. Масштабирование требует ключа 2GIS/Яндекс либо
ручного реестра доменов. Подробности — в [отчёте качества](docs/quality-report.md).

## Документация

- [План MVP](docs/PLAN.md) · [План v0.2](docs/PLAN-v0.2.md) · [Задачи](docs/TASKS.md)
- [Отчёт качества](docs/quality-report.md) · [Отчёт QA v0.2](docs/qa-report-v0.2.md) · [Словарь должностей](docs/roles-dictionary.md)
- [Интеграция](docs/INTEGRATION.md) · [Модель данных](docs/data-model.md) · [Источники](docs/sources-mvp.md)
- [Оркестрация агентов](docs/ORCHESTRATION.md)
