# Источники данных (реальные)

## Что используется сейчас

| Источник | Тип доступа | Ключ | Что даёт | Статус |
|----------|-------------|------|----------|--------|
| **OpenStreetMap / Nominatim** | публичный API | не нужен | название, адрес, город, иногда телефон/сайт | ✅ подключено |
| **Реестр официальных сайтов** `data/registry/official_sites.yaml` | HTTP HTML | не нужен | телефон, email, ФИО с публичных страниц | ✅ подключено |
| **Seed CSV** `data/seed/institutions.csv` | файл | не нужен | снимок OSM+sites (сейчас ~206 реальных POI) | ✅ |
| **2GIS Places API** | официальный API | `DGIS_API_KEY` | контакты, адреса по городам | ✅ код готов, нужен ключ |
| **Яндекс API Поиска по организациям** | официальный API | `YANDEX_MAPS_API_KEY` | организации + телефоны | ✅ код готов, нужен ключ |

## Важно про 2GIS / Яндекс.Карты

- HTML-страницы `2gis.ru` и `yandex.ru/maps` **не парсим** (нарушение ToS / антибот).
- Используем только **официальные HTTP API**.
- Ключи: [2GIS Platform](https://platform.2gis.ru/), [Яндекс Developer](https://developer.tech.yandex.ru/).

## Как запустить сбор

```bash
# Бесплатные источники (OSM + официальные сайты + seed)
PYTHONPATH=apps/api python scripts/crawl_real.py --source all_free

# Только OSM (долго: ~1 req/sec)
PYTHONPATH=apps/api python scripts/crawl_real.py --source osm

# 2GIS / Яндекс (нужны ключи в .env)
export DGIS_API_KEY=...
export YANDEX_MAPS_API_KEY=...
PYTHONPATH=apps/api python scripts/crawl_real.py --source 2gis
PYTHONPATH=apps/api python scripts/crawl_real.py --source yandex
PYTHONPATH=apps/api python scripts/crawl_real.py --source all

# Через API
curl -X POST http://localhost:8000/api/v1/admin/jobs/crawl \
  -H 'X-API-Key: YOUR_KEY' -H 'Content-Type: application/json' \
  -d '{"source":"all_free"}'
```

Источники `source`: `seed_csv` | `osm` | `sites` | `2gis` | `yandex` | `all_free` | `all` | `html`.

## Compliance

- User-Agent: `PerinatalContactsBot/0.1 (+github…)`
- Nominatim: ≤1 rps
- Allowlist доменов для HTML (anti-SSRF)
- Без обхода CAPTCHA/логинов

## Полнота полей

OSM часто без email/ФИО главного врача — добор:
1. 2GIS/Yandex API (телефоны/сайты)
2. `official_sites.yaml` + HTML collector
3. ручная верификация в Admin UI
