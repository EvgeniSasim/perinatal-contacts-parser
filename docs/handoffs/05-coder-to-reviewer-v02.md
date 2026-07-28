# Handoff: Coder → Reviewer (v0.2)

## Что сделано

### Модель данных

| Файл | Изменение |
|------|-----------|
| `apps/api/app/models.py` | `InstitutionPerson`, `CrawlAttempt`, enum `PersonRole`/`Confidence`/`CrawlStage`, `CONFIDENCE_RANK`, `JobKind.enrich` |
| `docs/data-model.md` | описание обеих таблиц, ключей upsert и индексов |

`institution_persons` — unique `(institution_id, full_name_norm, role)`, FK на `institutions` с `ON DELETE CASCADE`.

### Сбор данных

| Модуль | Роль |
|--------|------|
| `collectors/site_discovery.py` | поиск сайта: `existing` → `osm` → `2gis`; фильтр соцсетей и агрегаторов; `verify_site` проверяет живость и совпадение по городу/ключевым словам, с fallback на `http://` |
| `collectors/page_finder.py` | обход ≤2 уровня, ≤12 страниц, ≤1 rps, robots.txt, только тот же домен, 2 ретрая; приоритет страниц `leadership` > `contacts` > `departments` |
| `collectors/person_extractor.py` | блочное извлечение ФИО+должности, словарь ролей, антипаттерны, `confidence` |
| `services/enrich.py` | оркестратор, `crawl_attempts`, upsert персон, сбор email, запись денормализованных полей |
| `services/metrics.py` | метрики полноты |

### Ключевые решения, требующие внимания ревью

1. **Блочная привязка вместо окна символов.** ФИО берётся из самого глубокого элемента, где есть и ФИО, и должность (`_depth` в `ExtractedPerson`). Это единственное, что даёт приемлемую точность — проверено на 6 эталонных сайтах, 5/6 точных совпадений главврача, 6/6 после доработки обхода.
2. **`deputy` проверяется раньше `chief`**, потому что «заместитель главного врача» содержит «главного врача».
3. **Если у одного ФИО есть и `chief`, и `deputy`** — `chief` отбрасывается.
4. **`low` не попадает в `institutions.chief_physician`** — только в `institution_persons`.
5. **`verified_manually` защищает от перезаписи** парсером; ручная правка автоматически ставит `confidence = high`.
6. **`db.flush()` в `upsert_person`** обязателен: сессия создана с `autoflush=False`, без flush одна и та же персона со второй страницы того же сайта нарушает unique-констрейнт. Это был реальный сбой на botkinmoscow.ru.
7. **`_recently_failed`** не даёт повторно обходить домены, упавшие за последние 7 дней (обходится через `force=true`).

### API

Новое:

- `GET /api/v1/institutions/{id}/persons?min_confidence=` — публичный, по умолчанию скрывает `low`
- `GET /api/v1/institutions?has_chief=` — фильтр
- `POST /api/v1/admin/jobs/enrich`
- `GET /api/v1/admin/jobs/{job_id}`
- `GET /api/v1/admin/persons` — очередь проверки
- `PATCH|DELETE /api/v1/admin/persons/{id}` — с пересчётом полей учреждения
- `GET /api/v1/admin/metrics/completeness`
- `POST /api/v1/admin/mailings/preview`

Контракт `/institutions` не сломан — только добавлен параметр и поля уже существовали.

### UI, экспорт, рассылка

- Админка: 3 таба (Каталог / Полнота данных / Очередь проверки), карточка со списком персон и кнопкой «Подтвердить», кнопка «Обогатить».
- Исправлен баг экспорта: `window.location.href` уводил со страницы и ломал скачивание blob.
- Excel: второй лист `persons` с ролью, отделением, достоверностью и источником.
- Рассылка: подстановки `{{name}}`, `{{city}}`, `{{region}}`, `{{chief}}`, `{{address}}`; без ФИО `{{chief}}` → «коллеги»; предпросмотр показывает долю персонализированных писем.
- WP-плагин 0.2.0: вывод главврача, отделения патологии, сайта; атрибут и чекбокс `has_chief`.

### Тесты

`tests/test_persons.py` — 20 офлайн-тестов извлечения (ловушки: приёмная главврача, главбух, главная медсестра, отзывы, эпонимы «им. С.П. Боткина», ФИО через `<br>`, инициалы в двух порядках, приоритет патологии беременности).
`tests/test_api.py` — +8 тестов на персоны, метрики, `has_chief`, предпросмотр рассылки, лист `persons` в Excel.

Итого 36 passed, 1 skipped. `ruff check` чисто (добавлен `ruff.toml` с `line-length 120` и игнором E402 в `scripts/` и `tests/`, где `sys.path` правится до импортов).

## На что смотреть ревьюеру

1. Точность `chief_physician` — не пролезают ли секретари, главбухи, врачи-специалисты.
2. Compliance: robots.txt, rate limit, отсутствие парсинга HTML 2GIS/Яндекса, запрет произвольного URL от клиента.
3. Идемпотентность: повторный `enrich` не должен плодить дубли и терять ручные правки.
4. Безопасность: SSRF при обходе (URL берутся только из БД, не от клиента), XSS в админке (весь вывод через `esc()`).
5. Обработка ошибок: одно упавшее учреждение не должно ронять job.

## HANDOFF_READY: reviewer
