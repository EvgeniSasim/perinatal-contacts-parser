# Handoff: Analyst → Coder

## Scope MVP

Реализовать Epic B (B1–B11) строго по `docs/PLAN.md`, `docs/data-model.md`, `docs/sources-mvp.md`, `docs/openapi-v1.yaml`.

## Must-have

1. Monorepo: `apps/api`, `apps/web` (лёгкий admin), `apps/wp-plugin`, `data/seed`, `docker-compose.yml`.
2. PostgreSQL в Docker; для pytest — SQLite или testcontainers/postgres service.
3. Публичный list/get/filter/search; rejected скрыты по умолчанию.
4. Admin API за `X-API-Key` (ключ из env `ADMIN_API_KEY`, hash в БД опционально для MVP — сравнение с env достаточно).
5. Seed ≥100 строк CSV + команда загрузки.
6. Один HTML-коллектор с allowlist + fixture-тест.
7. Excel export async (job → файл в `storage/exports`).
8. Mailing: только dry-run по умолчанию (считает recipients, не шлёт).
9. Admin UI: таблица, q/type/region/city, карточка, кнопка Excel.
10. WP plugin: settings (api_url, api_key) + `[pnc_directory]`.
11. CI GitHub Actions: lint + pytest.

## Pragmatic defaults (согласовано Analyst)

- Admin UI: Next.js **или** Vite/React/static под `apps/web` — главное UX каталога.
- Очередь: для MVP можно sync-in-thread + таблица `jobs` без Celery; Redis опционален, но сервис в compose оставить.
- Playwright — stub/optional; httpx+BS4 обязателен.

## Do not

- Реальная массовая отправка без явного `dry_run=false` + `ALLOW_LIVE_MAIL=1`.
- Открытый proxy/fetch произвольных URL.
- Секреты в git.

## Acceptance smoke

```bash
docker compose up -d --build
curl -s localhost:8000/api/v1/health
curl -s 'localhost:8000/api/v1/institutions?page_size=5'
```

Seed загружен, total ≥ 100.

## Open questions (не блокеры)

- Прод-хост: если нет VPS — документировать compose-only deploy.
- Провайдер рассылки: отложить на v1.1.
