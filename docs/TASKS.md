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

## Итерация v0.2 — обогащение ФИО и email

План: `docs/PLAN-v0.2.md`. Причина: главврач заполнен у 1/482, патология у 0/482, email у 12/482.

### Epic E — Анализ обогащения (Agent 1: Analyst)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| E1 | Отчёт качества: заполненность по полям и регионам | analyst | done | `docs/quality-report.md` |
| E2 | Реестр 30 официальных сайтов для калибровки парсера | analyst | done | `data/registry/calibration_sites.yaml` |
| E3 | Словарь должностей и синонимов (главврач/зам/зав. патологией) | analyst | done | `docs/roles-dictionary.md` |
| E4 | Правила извлечения ФИО + уровни confidence | analyst | done | разделы в handoff 04 |
| E5 | Спека таблиц `institution_persons`, `crawl_attempts` | analyst | done | `docs/data-model.md` |
| E6 | Контракт новых эндпоинтов (persons, quality, enrich) | analyst | done | `docs/openapi-v1.yaml` |
| E7 | Handoff для Coder | analyst | done | `docs/handoffs/04-analyst-to-coder-v02.md` |

### Epic F — Обогащение и API (Agent 2: Coder)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| F1 | Миграции: `institution_persons`, `crawl_attempts`, поля completeness | coder | done | модели + `init_db` |
| F2 | Коллектор `site_discovery` — поиск официального домена | coder | done | проверено: OSM даёт 0 из 150, нужен ключ 2GIS |
| F3 | Коллектор `page_finder` — Руководство/Контакты/Отделения | coder | done | ≤12 страниц, robots.txt, ≤1 rps |
| F4 | Коллектор `person_extractor` — ФИО + должность + confidence | coder | done | 20 офлайн-тестов, блочная привязка |
| F5 | Связка «отделение патологии → зав. отделением» | coder | done | приоритет патологии беременности |
| F6 | Email-энричер со страниц контактов | coder | done | `_harvest_emails` при обходе |
| F7 | Кэш лучших персон в `institutions.chief_physician`/`pathology_head` | coder | done | `pick_field_values` + `_sync_institution_fields` |
| F8 | `GET /institutions/{id}/persons`, фильтры `has_chief`, `has_pathology_head` | coder | done | `/institutions/{id}/persons`, `has_chief` |
| F9 | `GET /meta/quality` + `POST /admin/jobs/enrich` | coder | done | `/admin/metrics/completeness`, `/admin/jobs/enrich` |
| F10 | Admin UI: колонка полноты, очереди пропусков, блок персон, кнопка «Обогатить» | coder | done | 3 таба, персоны в карточке, «Обогатить» |
| F11 | Excel: колонки персон и должностей | coder | done | лист `persons` в Excel |
| F12 | Рассылка: сегмент по роли + подстановки `{{full_name}}` | coder | done | подстановки + `/admin/mailings/preview` |
| F13 | Handoff к Reviewer | coder | done | `docs/handoffs/05-coder-to-reviewer-v02.md` |

### Epic G — Review (Agent 3: Reviewer)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| G1 | Точность извлечения ФИО: ложные срабатывания | reviewer | done | 8 ложных срабатываний найдено и устранено |
| G2 | Compliance: robots, rate-limit, allowlist, PII | reviewer | done | чеклист в handoff 06 — соблюдено |
| G3 | Контракт API vs OpenAPI (обратная совместимость) | reviewer | done | breaking changes нет |
| G4 | Идемпотентность обогащения и ре-краулинга | reviewer | done | повторный прогон не двоит персон |
| G5 | UX очередей ручной верификации | reviewer | done | таб «Очередь проверки» + подтверждение |
| G6 | Handoff к QA | reviewer | done | `docs/handoffs/06-reviewer-to-qa-v02.md` |

### Epic H — QA и релиз (Agent 4: QA & Deploy)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| H1 | Ручная валидация 50 случайных записей | qa_deploy | done | precision 95% (21 из 22), калибровка 6/6 |
| H2 | Проверка целей: chief ≥60%, pathology ≥25%, email ≥60% | qa_deploy | done | `docs/qa-report-v0.2.md` — цели не достигнуты, причина зафиксирована |
| H3 | Регресс: list/filter/search/export/WP | qa_deploy | done | 42 passed, ruff чисто |
| H4 | Прогон полного обогащения и снапшот seed | qa_deploy | done | `data/seed/institutions.csv` + `persons.csv` (560 персон) |
| H5 | Обновить `docs/INTEGRATION.md` (persons, quality) | qa_deploy | done | `docs/INTEGRATION.md` обновлён |
| H6 | Release `v0.2.0` | qa_deploy | done | tag v0.2.0 |

### Epic I — Пострелизное ревью v0.2 (Bugbot)

| ID | Задача | Владелец | Статус | DoD |
|----|--------|----------|--------|-----|
| I1 | Адресное обогащение по `institution_id` | coder | done | кнопка в карточке обогащает именно её; тест на подмену фильтрами |
| I2 | Денормализованные ФИО считать по всем персонам из БД | coder | done | `sync_institution_fields`, общая с админкой; тест «high не затирается medium» |
| I3 | Должность в соседнем блоке (`dt`/`dd`, `th`/`td`, заголовок) | coder | done | +1 главврач и +5 персон на 16 фикстурах, 4 теста на ложные пары |
| I4 | Экранирование подстановок в HTML-письме | coder | done | `render_template(..., html=True)`; тест на разметку в названии |
| I5 | robots.txt проверять тем же User-Agent | coder | done | `robots_allows` использует `BOT_UA`; тест на `Disallow` |
| I6 | Лимит запросов на домен при обходе | coder | done | `MAX_FETCHES = 30` — сайт с битыми ссылками не уводит обход в сотни запросов |
| I7 | Повторный прогон и обновление снапшота | qa_deploy | done | 100 учреждений, `data/seed/*.csv` обновлены |

---

## Порядок исполнения

```
v0.1.0 (выпущено)
A1–A7 (Analyst) ✓ → B1–B11 (Coder) ✓ → C1–C6 (Reviewer) ✓ → D1–D7 (QA) ✓ кроме D4

v0.2.0 (текущая цель)
E1–E7 (Analyst)
    ↓ handoff 04
F1–F13 (Coder)
    ↓ handoff 05
G1–G6 (Reviewer)
    ↓ handoff 06
H1–H6 (QA & Deploy)
```

D4 (прод-деплой) остаётся `blocked`: нужен запущенный Docker или доступ к VPS.

## Definition of Done продукта (MVP)

См. `docs/PLAN.md` → «Критерии готовности MVP».
