# Интеграция API и WordPress

## Базовый URL

Локально: `http://localhost:8000/api/v1`

Health: `GET /health`

## Публичные эндпоинты

```http
GET /institutions?q=&type=&region=&city=&has_email=&has_phone=&nmic_ref=&page=1&page_size=20&sort=name
GET /institutions/{id}
GET /meta/types
GET /meta/regions
GET /meta/stats
```

Пример:

```bash
curl 'http://localhost:8000/api/v1/institutions?region=Москва&page_size=10'
```

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
```

## WordPress

1. Скопировать `apps/wp-plugin/perinatal-contacts` в `wp-content/plugins/`.
2. Активировать плагин.
3. Settings → Perinatal Contacts: API URL = `https://YOUR_HOST/api/v1`.
4. Вставить shortcode:

```
[pnc_directory]
[pnc_directory region="Москва" type="womens_clinic"]
```

На фронте форма поиска использует query-параметры `pnc_q`, `pnc_region`, `pnc_city`, `pnc_type`.

## Admin UI

Открыть корень API: `http://localhost:8000/` — каталог, фильтры, Excel, dry-run рассылка.

## Docker

```bash
cp .env.example .env
COMPOSE_PROJECT_NAME=pnc docker compose up -d --build
```

Имя проекта обязательно, если путь репозитория содержит не-ASCII символы.
