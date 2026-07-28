# Бэклог задач

Статусы: `todo` · `in_progress` · `blocked` · `done` · `cancelled`

Владельцы: `analyst` · `coder` · `reviewer` · `qa_deploy`

---

## Epic A — Discovery и модель (Agent 1: Analyst)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| A1 | Уточнить таксономию типов учреждений и маппинг синонимов | analyst | done | таблица типов + примеры названий |
| A2 | Составить MVP-список источников (URL) по типам | analyst | done | ≥5 источников с оценкой полноты полей |
| A3 | Спека схемы БД (ER + поля + индексы FTS) | analyst | done | `docs/data-model.md` |
| A4 | OpenAPI-черновик `/api/v1` | analyst | done | `docs/openapi-v1.yaml` |
| A5 | Критерии качества данных и дедупа | analyst | done | правила match + verification_status |
| A6 | Разбить MVP на sprint-задачи для Coder | analyst | done | handoff `docs/handoffs/01-analyst-to-coder.md` |
| A7 | Ограничения: robots, rate-limit, PII, рассылки | analyst | done | чеклист compliance в sources-mvp |

---

## Epic B — Backend и парсер (Agent 2: Coder)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| B1 | Каркас monorepo: `apps/api`, `apps/web`, `apps/wp-plugin`, `packages/` | coder | done | README + структура |
| B2 | Docker Compose: api, db, redis, worker | coder | done | compose файл готов (daemon у QA) |
| B3 | Миграции PostgreSQL по data-model | coder | done | create_all (+ Alembic later) |
| B4 | CRUD + list/filter/search institutions | coder | done | тесты API зелёные |
| B5 | Auth: API key + admin JWT (минимально) | coder | done | X-API-Key на admin |
| B6 | Seed loader (CSV/JSON) + 1 HTML-коллектор | coder | done | 120 записей |
| B7 | Job: Excel export по фильтру | coder | done | файл скачивается по URL |
| B8 | Job stub: mailing campaign (dry-run) | coder | done | создаёт кампанию без реальной отправки |
| B9 | Admin UI: каталог, фильтры, карточка, экспорт | coder | done | `/` static UI |
| B10 | WP plugin: settings + shortcode directory | coder | done | `[pnc_directory]` |
| B11 | CI: lint + pytest + build | coder | done | GitHub Actions |

---

## Epic C — Review (Agent 3: Reviewer)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| C1 | Ревью архитектуры и границ модулей | reviewer | done | APPROVE |
| C2 | Security: secrets, SQL injection, SSRF scraper, API keys | reviewer | done | findings с severity |
| C3 | API contract vs реализация | reviewer | done | соответствует openapi |
| C4 | Качество парсера: rate-limit, idempotency, дедуп | reviewer | done | upsert + allowlist |
| C5 | UX Admin + WP: поиск/фильтры/a11y базово | reviewer | done | замечания minor |
| C6 | Handoff к QA | reviewer | done | `docs/handoffs/03-reviewer-to-qa.md` |

---

## Epic D — QA и деплой (Agent 4: QA & Deploy)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| D1 | Тест-план API / UI / WP | qa_deploy | done | `docs/test-plan.md` |
| D2 | Автотесты + ручной smoke | qa_deploy | done | 7/7 + smoke PASS |
| D3 | Фикс критичных багов (или тикеты Coder) | qa_deploy | done | нет blocker |
| D4 | Деплой: secrets, compose/prod, DNS/HTTPS | qa_deploy | blocked | Docker daemon / нет VPS |
| D5 | Smoke на проде: filter, search, export | qa_deploy | done | локальный uvicorn smoke |
| D6 | Документация интеграции WP + API keys | qa_deploy | done | `docs/INTEGRATION.md` |
| D7 | Tag release `v0.1.0` на GitHub | qa_deploy | done | https://github.com/EvgeniSasim/perinatal-contacts-parser/releases/tag/v0.1.0 |

---

## Порядок исполнения

```
A1–A7 (Analyst) ✓
    ↓ handoff 01
B1–B11 (Coder) ✓
    ↓ handoff 02
C1–C6 (Reviewer) ✓
    ↓ handoff 03
D1–D7 (QA & Deploy) — D4 blocked without Docker/VPS
```

## Definition of Done продукта (MVP)

См. `docs/PLAN.md` → «Критерии готовности MVP».
