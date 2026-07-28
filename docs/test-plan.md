# Test plan MVP

## Automated

```bash
PYTHONPATH=apps/api pytest -q
```

Ожидание: 7 passed (health, list≥100, filter/search, export auth, mailing dry-run, HTML fixture, SSRF block).

## Manual smoke

1. `GET /api/v1/health` → `{"status":"ok"}`
2. `GET /api/v1/institutions?page_size=5` → total ≥ 100
3. Search `q=НМИЦ` → ≥1
4. Admin UI `/` открывается
5. `POST /api/v1/admin/export` с API key → xlsx
6. `POST /api/v1/admin/mailings` dry-run → skipped_count > 0
7. WP shortcode — на стенде с плагином (опционально)

## Results 2026-07-28

| Check | Result |
|-------|--------|
| pytest | PASS 7/7 |
| health | PASS |
| list 120 | PASS |
| search НМИЦ | PASS |
| export | PASS |
| mailing dry-run | PASS |
| admin UI | PASS |
| docker compose | BLOCKED (Docker daemon not running) |
| prod VPS deploy | BLOCKED (нет сервера/секретов) |
