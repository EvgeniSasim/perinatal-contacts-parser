# Handoff: Reviewer → QA

## Verdict: APPROVE (с оговорками)

MVP готов к QA и compose-деплою. Критичных блокеров безопасности нет для локального/VPS MVP.

## Findings

| Sev | Finding | Рекомендация |
|-----|---------|--------------|
| 🟡 | Нет Alembic — только `create_all` | добавить миграции до прод-данных |
| 🟡 | Admin API key в env plaintext compare | ок для MVP; позже hash в БД |
| 🟡 | Export/mailing sync в request thread | ок до ~10k строк; потом queue |
| 🟡 | CORS `*` по умолчанию | сузить в проде |
| 🟢 | Deprecation `on_event` | lifespan |
| 🟢 | Redis в compose без использования | оставить под v1.1 |

## Security checklist

- [x] Нет секретов в git (`.env` в gitignore)
- [x] Admin routes требуют `X-API-Key`
- [x] Scraper allowlist / SSRF blocked (тест есть)
- [x] page_size ≤ 100
- [x] Mailing dry-run по умолчанию / live требует флаг
- [x] WP: escape output, capability на settings
- [ ] Docker health — проверить когда daemon доступен

## HANDOFF_READY: qa_deploy
