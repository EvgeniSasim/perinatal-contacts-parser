# Модель данных

## ER (логически)

```
institutions 1───* institution_phones
institutions 1───* institution_emails
institutions *───1 crawl_sources (optional)
jobs (export / crawl / mailing)
mail_campaigns 1───* mail_recipients (snapshot emails)
api_keys
```

## Таблица `institutions`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | VARCHAR(512) NOT NULL | |
| type | VARCHAR(64) NOT NULL | enum string |
| region | VARCHAR(256) NOT NULL | субъект РФ |
| city | VARCHAR(256) NOT NULL | |
| address | TEXT NOT NULL | |
| website | VARCHAR(1024) NULL | |
| chief_physician | VARCHAR(256) NULL | |
| pathology_head | VARCHAR(256) NULL | |
| nmic_ref | VARCHAR(256) NULL | название/код НМИЦ |
| source_url | VARCHAR(2048) NOT NULL | |
| verification_status | VARCHAR(32) NOT NULL | `pending`/`verified`/`rejected` |
| phones_json | JSONB NOT NULL DEFAULT `[]` | нормализованные E.164-ish |
| emails_json | JSONB NOT NULL DEFAULT `[]` | lowercased |
| name_norm | VARCHAR(512) | для дедупа |
| phone_primary_norm | VARCHAR(32) | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

Индексы: `(type)`, `(region)`, `(city)`, GIN по `to_tsvector(name \|\| address)`, btree `phone_primary_norm`, unique partial на `(name_norm, city)` где verified.

## Типы (`type`)

| code | label | синонимы |
|------|-------|----------|
| perinatal_center | Перинатальный центр | ПЦ |
| perinatal_center_regional | Областной перинатальный центр | ОПЦ, краевой ПЦ |
| perinatal_center_city | Городской клинический перинатальный центр | ГКПЦ |
| womens_clinic | Женская консультация | ЖК |
| maternity_hospital | Родильный дом | роддом, РД |
| obgyn_clinic | Клиника акушерства и гинекологии | |
| obgyn_chair | Кафедра акушерства и гинекологии | |
| nmic | НМИЦ акушерства и гинекологии | НЦАГиП |

## `jobs`

| Column | Type |
|--------|------|
| id | UUID |
| kind | `crawl`/`export`/`mailing` |
| status | `queued`/`running`/`done`/`failed` |
| payload_json | JSONB |
| result_json | JSONB |
| error | TEXT |
| created_at / finished_at | TIMESTAMPTZ |

## `mail_campaigns`

| Column | Type |
|--------|------|
| id | UUID |
| subject | VARCHAR |
| body_html | TEXT |
| filter_json | JSONB |
| dry_run | BOOLEAN DEFAULT true |
| status | queued/running/done/failed |
| sent_count / skipped_count | INT |
| created_at | TIMESTAMPTZ |

## `api_keys`

| Column | Type |
|--------|------|
| id | UUID |
| name | VARCHAR |
| key_hash | VARCHAR | sha256 |
| scopes | JSONB | `["read","admin","export","mailing"]` |
| created_at | TIMESTAMPTZ |
| revoked_at | TIMESTAMPTZ NULL |

## Дедуп

1. Нормализация: lower, ё→е, убрать ООО/ГБУЗ префиксы из name_norm.
2. Телефон: только цифры, 8XXXXXXXXXX → 7XXXXXXXXXX.
3. Match: одинаковый `phone_primary_norm` ИЛИ (`name_norm` + `city`) similarity > 0.85.
4. При конфликте — merge phones/emails, source_url → массив в result audit (MVP: последний source_url).

## verification_status

- `pending` — из парсера/seed
- `verified` — ручная проверка в админке
- `rejected` — скрыть из публичного API (фильтр по умолчанию: не rejected)
