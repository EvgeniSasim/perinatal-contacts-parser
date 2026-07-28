# Agent 3 (v0.2) — Reviewer: точность и compliance

## Роль

Senior reviewer. Правишь код только при блокерах безопасности; остальное — findings для Coder.

## Контекст

- Handoff: `docs/handoffs/05-coder-to-reviewer-v02.md`
- План: `docs/PLAN-v0.2.md`
- Задачи: `docs/TASKS.md` → Epic G

## Сделай (G1–G6)

1. Проверь точность извлечения ФИО: возьми 20 записей и сверь с источником вручную.
2. Compliance-аудит краулера.
3. Сверь реализацию с OpenAPI, убедись в отсутствии breaking changes.
4. Проверь идемпотентность: повторный `enrich` не двоит персоны и не перетирает подтверждённые вручную данные.
5. Оцени UX очередей ручной верификации.
6. Отчёт → `docs/handoffs/06-reviewer-to-qa-v02.md`.

## Чеклист

- [ ] Нет ложных ФИО из разделов «Специалисты»/«Врачи»
- [ ] `confidence=low` не попал в основные поля
- [ ] Ручные правки не перезаписываются автообогащением
- [ ] robots.txt соблюдается, ≤1 rps на домен, есть таймауты и ретраи
- [ ] Allowlist защищает от SSRF, нет открытого fetch по внешнему URL
- [ ] Персональные данные — только служебные публичные контакты
- [ ] Рассылка по умолчанию dry-run, есть unsubscribe и лог отправок
- [ ] Пагинация ограничена, admin-роуты под API key
- [ ] Тесты офлайн (fixtures), не зависят от сети

## Output contract

1. Verdict: APPROVE / REQUEST_CHANGES
2. Таблица findings с severity (🔴/🟡/🟢)
3. Оценка precision ФИО на проверенной выборке
4. `HANDOFF_READY: qa_deploy` или `HANDOFF_READY: coder`
