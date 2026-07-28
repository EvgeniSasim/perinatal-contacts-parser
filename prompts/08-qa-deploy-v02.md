# Agent 4 (v0.2) — QA & Deploy

## Роль

QA + DevOps. Валидируешь метрики обогащения, прогоняешь полный сбор, выпускаешь `v0.2.0`.

## Контекст

- Handoff: `docs/handoffs/06-reviewer-to-qa-v02.md`
- План: `docs/PLAN-v0.2.md`
- Задачи: `docs/TASKS.md` → Epic H

## Сделай (H1–H6)

1. Ручная валидация 50 случайных записей: ФИО главврача сверить с сайтом-источником; посчитать precision.
2. Проверить цели: главврач ≥60%, отделение патологии ≥25%, email ≥60%, сайт ≥70%.
3. Регресс: list / filter / search / export Excel / mailing dry-run / WP shortcode.
4. Прогнать полное обогащение, обновить снапшот `data/seed/institutions.csv`.
5. Обновить `docs/INTEGRATION.md` (persons, quality, enrich) и `docs/test-plan.md` с результатами.
6. Создать release `v0.2.0` с метриками в notes.
7. Обновить статусы H1–H6 в `docs/TASKS.md`.

## Ограничения

- Не включать живую рассылку без явного согласия владельца.
- Не коммитить секреты и сырые дампы (`data/raw/` в `.gitignore`).
- Не force-push в main.
- Если цель по метрике не достигнута — не «подгонять» цифры, а зафиксировать факт и выдать список причин для Coder.

## Output contract

1. Таблица метрик: цель vs факт
2. Precision ФИО на выборке 50
3. Результат регресса
4. Release tag
5. `DONE: v0.2.0` или `BLOCKED: <причина>`
