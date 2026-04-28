# Отладка

Этот файл нужен для первой помощи, когда кэпстоун-проект не запускается или
артефакты выглядят странно.

## Что приложить к вопросу

Не присылайте `.env`, `OPENAI_API_KEY` и другие секреты. Вместо этого приложите:

1. ОС и вывод `uv --version`;
2. commit SHA;
3. точную команду, которая упала;
4. первые строки ошибки;
5. если есть `run_id`: `artifacts/runs/<run_id>.json`,
   `artifacts/health/<run_id>.json` и последние строки
   `artifacts/traces/<run_id>.jsonl`.

## Базовый путь не проходит

Проверьте, что вы находитесь в корне репозитория:

```bash
pwd
ls README.md pyproject.toml
```

Затем повторите базовый путь:

```bash
uv sync --frozen --extra dev
uv run --with pytest python -m pytest
uv run kb-agent --query-fixture fixtures/queries/m0_query.json --vault-root vault
uv run kb-eval --eval-fixture fixtures/evals/cases.json --vault-root vault
```

## Не появились `vault/wiki/` или `artifacts/`

В чистом клоне есть только `vault/raw/`. Производные файлы появляются после:

```bash
uv run kb-agent --query-fixture fixtures/queries/m0_query.json --vault-root vault
```

После успешного запуска в выводе должен появиться `run_id` и пути к `context`,
`trace`, `health` и `answer`.

## Нужно начать заново

Можно удалить только производные артефакты:

```bash
rm -rf artifacts vault/wiki vault/outputs vault/index.md vault/log.md
```

Команда не трогает `vault/raw/`.

## Live OpenAI-запуск не проходит

Live-путь опционален. Он нужен только для финального ответа через Responses API.

Проверьте:

1. переменная `OPENAI_API_KEY` задана в текущем терминале;
2. вы запускаете команду из корня репозитория;
3. базовый deterministic-путь без `--live-openai` уже проходит;
4. вы не публикуете ключ в логах и скриншотах.

Команда live-пути:

```bash
OPENAI_API_KEY=... uv run --extra openai kb-agent --query-fixture fixtures/queries/m0_query.json --vault-root vault --live-openai
```

## Health или eval вернули fail

Сначала откройте:

1. `artifacts/health/<run_id>.json`;
2. `artifacts/traces/<run_id>.jsonl`;
3. `vault/outputs/<run_id>-summary.md`;
4. `artifacts/context/<run_id>.json`.

Ищите не «плохой ответ вообще», а конкретный слой: нет файла, пустой контекст,
не совпали источники, не создан eval-отчёт или запуск завершился не тем
`terminal_reason`.

Если нужен маршрут «куда смотреть по шагам», используйте `docs/runbook.md`.
