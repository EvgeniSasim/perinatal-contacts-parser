# Источники MVP

Целевой объём seed для MVP: **≥100** записей (смешанные типы, ≥15 регионов).

## Приоритет источников

| # | Источник | Тип данных | Полнота полей | Метод |
|---|----------|------------|---------------|-------|
| 1 | Seed CSV проекта (`data/seed/institutions.csv`) | все типы | высокая (кураторский) | loader |
| 2 | Публичные страницы НМИЦ АГ (ncagp.ru и аналоги) | nmic + ссылки | средняя | HTML httpx+BS4 |
| 3 | Региональные минздравы / списки ПЦ | perinatal_* | средняя | HTML |
| 4 | Сайты учреждений (добор) | phones/email/ФИО | низкая–средняя | httpx, позже Playwright |
| 5 | Открытые справочники субъектов РФ | ЖК/роддома | низкая | ручной CSV |

## MVP-коллекторы (реализация)

1. **`seed_csv`** — обязательный, идемпотентный upsert по name_norm+city.
2. **`html_list_generic`** — конфиг: URL + CSS/regex селекторы из YAML; один рабочий пример на статическом fixture + опционально live URL.

Live-краулинг без allowlist доменов **запрещён** (SSRF).

## Оценка полей по источникам

| Поле | seed | nmic html | site enrich |
|------|------|-----------|-------------|
| address | ✓ | ✓ | ✓ |
| phones | ✓ | ~ | ✓ |
| emails | ✓ | ~ | ✓ |
| chief_physician | ✓ | ~ | ~ |
| pathology_head | ✓ | ✗ | ~ |
| nmic_ref | ✓ | ✓ | ✗ |

## Compliance

- Только публичный HTML/CSV.
- Rate limit: ≤1 rps на домен, jitter.
- User-Agent: `PerinatalContactsBot/0.1 (+https://github.com/EvgeniSasim/perinatal-contacts-parser)`.
- Уважать robots.txt; при Disallow — skip + log.
- Не обходить CAPTCHA/auth.
