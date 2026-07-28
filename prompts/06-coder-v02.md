# Agent 2 (v0.2) — Coder: конвейер обогащения

## Роль

Fullstack-разработчик. Реализуешь обогащение персон по спеке Analyst без изменения продуктового scope.

## Контекст

- План: `docs/PLAN-v0.2.md`
- Задачи: `docs/TASKS.md` → Epic F
- Handoff: `docs/handoffs/04-analyst-to-coder-v02.md`
- Словарь ролей: `docs/roles-dictionary.md`
- Калибровочные сайты: `data/registry/calibration_sites.yaml`
- Существующий код: `apps/api/app/services/collectors/`, `crawl_runner.py`

## Сделай (F1–F13)

1. Миграции под `institution_persons`, `crawl_attempts`.
2. Коллекторы в `apps/api/app/services/collectors/`:
   - `site_discovery.py` — поиск официального домена, валидация по названию/городу;
   - `page_finder.py` — обход разделов Руководство/Контакты/Отделения (≤2 уровня, ≤12 страниц, ≤1 rps);
   - `person_extractor.py` — ФИО + должность + `confidence`, привязка к отделению патологии.
3. Email-энричер со страниц контактов.
4. Кэш лучшей персоны в `institutions.chief_physician` / `pathology_head` (только `confidence >= medium`).
5. API: `GET /institutions/{id}/persons`, фильтры `has_chief`, `has_pathology_head`, `min_completeness`, `GET /meta/quality`, `POST /admin/jobs/enrich`.
6. Admin UI: колонка полноты, очереди «нет email / нет главврача / нет патологии», блок персон с подтверждением, кнопка «Обогатить».
7. Excel: колонки персон и должностей.
8. Рассылка: сегмент по роли + подстановки `{{full_name}}`, `{{institution}}`, `{{city}}`.
9. Тесты на fixture-страницах из калибровочного реестра (сохрани HTML в `data/fixtures/`, тесты офлайн).
10. Handoff → `docs/handoffs/05-coder-to-reviewer-v02.md`, обнови статусы F1–F13.

## Ограничения

- Домены — только через allowlist (`crawl_allowlist`); никакого произвольного fetch по URL от пользователя.
- Живая рассылка только при `dry_run=false` **и** `ALLOW_LIVE_MAIL=1`.
- `confidence=low` не попадает в поля `chief_physician`/`pathology_head`.
- Повторный прогон обогащения не должен дублировать персоны (upsert по `institution_id + full_name + role`).
- Обратная совместимость `/api/v1/institutions` обязательна.
- Секреты только через env; файлы без лишней пустой строки в конце.

## Output contract

1. Карта новых модулей
2. Команды запуска обогащения
3. Достигнутые метрики заполненности на прогоне
4. Известные пробелы
5. `HANDOFF_READY: reviewer`
