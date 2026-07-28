# Бэклог задач

Статусы: `todo` · `in_progress` · `blocked` · `done` · `cancelled`

Владельцы: `analyst` · `coder` · `reviewer` · `qa_deploy`

---

## Epic A — Discovery и модель (Agent 1: Analyst)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| A1 | Уточнить таксономию типов учреждений и маппинг синонимов | analyst | todo | таблица типов + примеры названий |
| A2 | Составить MVP-список источников (URL) по типам | analyst | todo | ≥5 источников с оценкой полноты полей |
| A3 | Спека схемы БД (ER + поля + индексы FTS) | analyst | todo | `docs/data-model.md` |
| A4 | OpenAPI-черновик `/api/v1` | analyst | todo | `docs/openapi-v1.yaml` или раздел в handoff |
| A5 | Критерии качества данных и дедупа | analyst | todo | правила match + verification_status |
| A6 | Разбить MVP на sprint-задачи для Coder | analyst | todo | handoff `docs/handoffs/01-analyst-to-coder.md` |
| A7 | Ограничения: robots, rate-limit, PII, рассылки | analyst | todo | чеклист compliance в handoff |

---

## Epic B — Backend и парсер (Agent 2: Coder)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| B1 | Каркас monorepo: `apps/api`, `apps/web`, `apps/wp-plugin`, `packages/` | coder | todo | README + структура |
| B2 | Docker Compose: api, db, redis, worker | coder | todo | `docker compose up` поднимает health |
| B3 | Миграции PostgreSQL по data-model | coder | todo | Alembic apply clean |
| B4 | CRUD + list/filter/search institutions | coder | todo | тесты API зелёные |
| B5 | Auth: API key + admin JWT (минимально) | coder | todo | защищённые admin-роуты |
| B6 | Seed loader (CSV/JSON) + 1 HTML-коллектор | coder | todo | ≥100 записей в dev DB |
| B7 | Job: Excel export по фильтру | coder | todo | файл скачивается по URL |
| B8 | Job stub: mailing campaign (dry-run) | coder | todo | создаёт кампанию без реальной отправки |
| B9 | Admin UI: каталог, фильтры, карточка, экспорт | coder | todo | usable локально |
| B10 | WP plugin: settings + shortcode directory | coder | todo | рендер списка из API |
| B11 | CI: lint + pytest + build | coder | todo | GitHub Actions green |

---

## Epic C — Review (Agent 3: Reviewer)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| C1 | Ревью архитектуры и границ модулей | reviewer | todo | отчёт без критичных блокеров или список блокеров |
| C2 | Security: secrets, SQL injection, SSRF scraper, API keys | reviewer | todo | findings с severity |
| C3 | API contract vs реализация | reviewer | todo | diff контракта |
| C4 | Качество парсера: rate-limit, idempotency, дедуп | reviewer | todo | замечания / approve |
| C5 | UX Admin + WP: поиск/фильтры/a11y базово | reviewer | todo | замечания |
| C6 | Handoff к QA | reviewer | todo | `docs/handoffs/03-reviewer-to-qa.md` |

---

## Epic D — QA и деплой (Agent 4: QA & Deploy)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| D1 | Тест-план API / UI / WP | qa_deploy | todo | `docs/test-plan.md` |
| D2 | Автотесты + ручной smoke | qa_deploy | todo | отчёт pass/fail |
| D3 | Фикс критичных багов (или тикеты Coder) | qa_deploy | todo | MVP blockers closed |
| D4 | Деплой: secrets, compose/prod, DNS/HTTPS | qa_deploy | todo | публичный health `/health` |
| D5 | Smoke на проде: filter, search, export | qa_deploy | todo | чеклист подписан |
| D6 | Документация интеграции WP + API keys | qa_deploy | todo | `docs/INTEGRATION.md` |
| D7 | Tag release `v0.1.0` на GitHub | qa_deploy | todo | release notes |

---

## Порядок исполнения

```
A1–A7 (Analyst)
    ↓ handoff 01
B1–B11 (Coder)
    ↓ handoff 02 (PR / summary)
C1–C6 (Reviewer)
    ↓ handoff 03
D1–D7 (QA & Deploy)
```

Параллелить можно только после стабилизации контракта: B9/B10 после B4; C* только после mergeable ветки.

## Definition of Done продукта (MVP)

См. `docs/PLAN.md` → «Критерии готовности MVP».
