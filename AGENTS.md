# Рабочий контракт агента

Этот файл нужен студенту и любому кодинг-агенту, который открывает репозиторий.
Он фиксирует, как безопасно работать с учебным кэпстоун-проектом.

## Главная рамка

`llm-wiki-agent` — учебный агент корпоративной LLM Wiki для Northstar Compute.
Базовый путь курса заканчивается проектным маршрутом: raw-источники, wiki-слой,
пакет контекста, ответ, трейс, проверка состояния и mini-evals.

Не превращайте базовый срез в большой production-runtime. Расширения с обратной
записью, очередями, деплоем и большим regression harness описаны в
`docs/roadmap.md`.

## Что можно менять в базовом срезе

1. Код, который улучшает читаемый путь `raw -> wiki -> context -> answer`.
2. Документацию, если она делает маршрут студента яснее.
3. Тесты и eval-кейсы, если они проверяют уже изученные идеи.
4. Синтетический корпус Northstar Compute в `vault/raw/`, если нужна маленькая
   учебная правка лора.

## Что нельзя делать без отдельного решения

1. Писать в `vault/raw/` или `vault/wiki/` по инициативе модели во время live-запуска.
2. Добавлять обязательный web crawling, внешние search API или social API.
3. Делать «Живую Wiki» с обратной записью обязательной частью сдачи.
4. Требовать hosted deployment, RBAC, queues или multi-agent orchestration для
   базовой сдачи.
5. Публиковать `.env`, `OPENAI_API_KEY`, токены или приватные URL.

## Канонические команды

```bash
uv sync --frozen --extra dev
uv run pytest
uv run kb-agent --query-fixture fixtures/queries/project_query.json --vault-root vault
uv run kb-eval --eval-fixture fixtures/evals/cases.json --vault-root vault
```

Опциональный live-путь:

```bash
OPENAI_API_KEY=... uv run --extra openai kb-agent --query-fixture fixtures/queries/project_query.json --vault-root vault --live-openai
```

В этом репозитории нет обязательных `just`-команд, веток или специальных
git-операций для сдачи.

## Артефакты, которые нужно читать первыми

1. `vault/outputs/<run_id>-summary.md`
2. `vault/outputs/<run_id>.md`
3. `artifacts/context/<run_id>.json`
4. `artifacts/traces/<run_id>.jsonl`
5. `artifacts/health/<run_id>.json`
6. `artifacts/evals/<eval_run_id>.json`

## Перед передачей работы

Заполните короткий шаблон из `docs/handoff-template.md`. Он не нужен для
формальности: по нему видно, какой `run_id` проверялся, какие команды прошли и
где искать доказательства.

Если студент застрял, сначала откройте `docs/student-help.md`: там коротко
описано, что приложить к вопросу, как читать артефакты по `run_id` и какие
секреты нельзя публиковать.
