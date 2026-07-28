# Оркестрация агентов

Запускай агентов **последовательно** в отдельных чатах Cursor. Копируй содержимое соответствующего файла из `prompts/` и прикрепляй нужные `@docs/...`.

## Последовательность

1. **Analyst** — `@prompts/01-analyst.md` + `@docs/PLAN.md` + `@docs/TASKS.md`  
   Жди: `HANDOFF_READY: coder`
2. **Coder** — `@prompts/02-coder.md` + `@docs/handoffs/01-analyst-to-coder.md`  
   Жди: `HANDOFF_READY: reviewer`
3. **Reviewer** — `@prompts/03-reviewer.md` + `@docs/handoffs/02-coder-to-reviewer.md`  
   Жди: `HANDOFF_READY: qa_deploy` (или возврат coder)
4. **QA & Deploy** — `@prompts/04-qa-deploy.md` + `@docs/handoffs/03-reviewer-to-qa.md`  
   Жди: `DONE: mvp`

## Итерация v0.2 — обогащение ФИО и email

План: `docs/PLAN-v0.2.md`, задачи: Epic E–H в `docs/TASKS.md`.

1. **Analyst** — `@prompts/05-analyst-v02.md` + `@docs/PLAN-v0.2.md` + `@docs/TASKS.md`
   Жди: `HANDOFF_READY: coder`
2. **Coder** — `@prompts/06-coder-v02.md` + `@docs/handoffs/04-analyst-to-coder-v02.md`
   Жди: `HANDOFF_READY: reviewer`
3. **Reviewer** — `@prompts/07-reviewer-v02.md` + `@docs/handoffs/05-coder-to-reviewer-v02.md`
   Жди: `HANDOFF_READY: qa_deploy`
4. **QA & Deploy** — `@prompts/08-qa-deploy-v02.md` + `@docs/handoffs/06-reviewer-to-qa-v02.md`
   Жди: `DONE: v0.2.0`

## Репозиторий

https://github.com/EvgeniSasim/perinatal-contacts-parser

## Локальный статус handoff

Папка `docs/handoffs/` заполняется агентами по мере работы.
