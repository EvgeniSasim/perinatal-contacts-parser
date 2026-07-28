# Интеграция API и WordPress

## Базовый URL

Локально: `http://localhost:8000/api/v1`

Health: `GET /health`

## Публичные эндпоинты

```http
GET /institutions?q=&type=&region=&city=&has_email=&has_phone=&has_chief=&nmic_ref=&page=1&page_size=20&sort=name
GET /institutions/{id}
GET /institutions/{id}/persons?min_confidence=medium
GET /meta/types
GET /meta/regions
GET /meta/stats
```

Пример:

```bash
curl 'http://localhost:8000/api/v1/institutions?region=Москва&page_size=10'

# только учреждения с известным главврачом
curl 'http://localhost:8000/api/v1/institutions?has_chief=true&page_size=10'

# все персоны учреждения, включая низкую достоверность
curl 'http://localhost:8000/api/v1/institutions/{id}/persons?min_confidence=low'
```

### Персоны и достоверность

`GET /institutions/{id}/persons` возвращает руководство и заведующих отделениями:

| Поле | Значение |
|------|----------|
| `role` | `chief`, `deputy`, `pathology_head`, `head`, `other` |
| `confidence` | `high` — ФИО и должность в одном блоке на странице руководства; `medium` — на странице контактов или отделений; `low` — роль угадана |
| `verified_manually` | подтверждено вручную, парсер такую запись не перезаписывает |
| `source_url` | страница, откуда взято — для проверки |

По умолчанию `low` скрыт. Поля `chief_physician` и `pathology_head` в самом учреждении —
это лучший кандидат из `high`/`medium`, чтобы не делать второй запрос для списков.

## Admin (заголовок `X-API-Key`)

Ключ: env `ADMIN_API_KEY` (в `.env.example`: `dev-admin-key-change-me`).

```bash
# Excel по фильтру
curl -X POST http://localhost:8000/api/v1/admin/export \
  -H 'X-API-Key: YOUR_KEY' -H 'Content-Type: application/json' \
  -d '{"region":"Москва","has_email":true}'

# Скачать файл
curl -OJ -H 'X-API-Key: YOUR_KEY' \
  http://localhost:8000/api/v1/admin/export/{job_id}/file

# Рассылка dry-run
curl -X POST http://localhost:8000/api/v1/admin/mailings \
  -H 'X-API-Key: YOUR_KEY' -H 'Content-Type: application/json' \
  -d '{"subject":"Тема","body_html":"<p>Текст</p>","dry_run":true,"filter":{"has_email":true}}'

# Предпросмотр с подстановками
curl -X POST http://localhost:8000/api/v1/admin/mailings/preview \
  -H 'X-API-Key: YOUR_KEY' -H 'Content-Type: application/json' \
  -d '{"subject":"Приглашение для {{name}}","body_html":"<p>Уважаемый(ая) {{chief}}!</p>","filter":{"has_chief":true}}'

# Обогащение: найти ФИО руководства и email на сайтах учреждений
curl -X POST http://localhost:8000/api/v1/admin/jobs/enrich \
  -H 'X-API-Key: YOUR_KEY' -H 'Content-Type: application/json' \
  -d '{"limit":25,"only_missing_chief":true,"with_site_only":true}'

# Метрики полноты
curl -H 'X-API-Key: YOUR_KEY' http://localhost:8000/api/v1/admin/metrics/completeness

# Очередь ручной проверки и подтверждение персоны
curl -H 'X-API-Key: YOUR_KEY' 'http://localhost:8000/api/v1/admin/persons?role=chief&unverified_only=true'
curl -X PATCH -H 'X-API-Key: YOUR_KEY' -H 'Content-Type: application/json' \
  -d '{"verified_manually":true}' http://localhost:8000/api/v1/admin/persons/{person_id}
```

### Подстановки в рассылке

`{{name}}`, `{{city}}`, `{{region}}`, `{{chief}}`, `{{address}}`. Если ФИО главврача
неизвестно, `{{chief}}` подставляется как «коллеги» — письмо остаётся корректным.

### Обогащение из командной строки

```bash
python3 scripts/enrich.py --limit 100 --with-site-only --verbose
python3 scripts/enrich.py --region "Москва" --force
python3 scripts/enrich.py --report          # только метрики, без обхода
```

## WordPress

1. Скопировать `apps/wp-plugin/perinatal-contacts` в `wp-content/plugins/`.
2. Активировать плагин.
3. Settings → Perinatal Contacts: API URL = `https://YOUR_HOST/api/v1`.
4. Вставить shortcode:

```
[pnc_directory]
[pnc_directory region="Москва" type="womens_clinic"]
[pnc_directory type="perinatal_center" has_chief="1"]
```

На фронте форма поиска использует query-параметры `pnc_q`, `pnc_region`, `pnc_city`,
`pnc_type`, `pnc_has_chief`. В карточке выводятся телефоны, email, сайт, главный врач и
заведующий отделением патологии.

## Admin UI

Открыть корень API: `http://localhost:8000/`.

| Таб | Что делает |
|-----|-----------|
| Каталог | поиск и фильтры, карточка учреждения со списком персон и кнопкой «Подтвердить», Excel, рассылка с предпросмотром |
| Полнота данных | заполненность полей в процентах, разрез по типам учреждений, статистика шагов обхода |
| Очередь проверки | персоны с фильтром по роли и достоверности, массовое подтверждение |

Кнопка «Обогатить» запускает обход сайтов для 25 учреждений без главврача (с учётом
выбранных региона и типа). Обход занимает несколько минут — это синхронный job.

## Docker

```bash
cp .env.example .env
COMPOSE_PROJECT_NAME=pnc docker compose up -d --build
```

Имя проекта обязательно, если путь репозитория содержит не-ASCII символы.
