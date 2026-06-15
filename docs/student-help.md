# Помощь студенту

Этот файл нужен, когда первый запуск кэпстоун-проекта не проходит или вы не
понимаете, какие артефакты приложить в LMS. Держите его коротким: цель не
написать отчёт, а быстро показать состояние проекта.

## Что приложить к вопросу

Не присылайте `.env`, `OPENAI_API_KEY`, токены и приватные URL.

Достаточно такого пакета:

1. ОС и вывод `uv --version`;
2. commit SHA или ссылка на вашу версию репозитория;
3. точная команда, которая упала;
4. первые строки ошибки;
5. если появился `run_id`: `vault/outputs/<run_id>-summary.md`;
6. если есть `run_id`: `artifacts/health/<run_id>.json`;
7. последние 10-20 строк `artifacts/traces/<run_id>.jsonl`.

Если ошибка случилась до появления `run_id`, так и напишите: «run_id ещё не
появился». Это нормальная диагностическая информация.

## Куда смотреть по `run_id`

Один `run_id` связывает все доказательства одного запуска.

Берите `run_id` из вывода команды `kb-agent`. `eval_run_id` из `kb-eval` — это
отдельный идентификатор проверочного прогона, он не заменяет основной запуск.

1. `vault/outputs/<run_id>-summary.md` — первая страница для чтения.
2. `vault/outputs/<run_id>.md` — итоговый ответ.
3. `artifacts/source-map/<run_id>.json` — какие raw-источники поддерживают ответ.
4. `artifacts/context/<run_id>.json` — что попало в модельный контекст.
5. `artifacts/traces/<run_id>.jsonl` — что происходило по шагам.
6. `artifacts/health/<run_id>.json` — прошла ли проверка состояния.
7. `artifacts/tools/<run_id>.json` — какие тулы read-only, а какие пишут.
8. `artifacts/evals/<eval_run_id>.json` — результат eval-запуска.

Если вы не можете связать ответ, source-map, контекст, трейс и health одним `run_id`,
сначала не чините код: восстановите карту артефактов.

Source-map и context отвечают на разные вопросы. Context показывает, что было
передано модели. Source-map показывает, какие raw-источники поддерживают
готовый ответ.

В context JSON полезнее всего смотреть `plan_step_context[].selected_raw_documents`
и `raw_documents`: там видно, какие raw-источники попали в основание ответа.

## Частые ситуации

**Команда не видит проект.**  
Проверьте, что терминал открыт в корне репозитория:

```bash
pwd
ls README.md pyproject.toml
```

**Зависимости не встали.**  
Повторите базовую установку:

```bash
uv sync --frozen --extra dev
```

**Локальный запуск прошёл, но eval упал.**  
Откройте eval-отчёт и найдите первый failed case. Обычно проблема не в «плохой
модели», а в выбранном контексте, цитате, grounding или недостаточном evidence.

**Live OpenAI-путь не запускается.**  
Это не блокер базовой сдачи. Сначала должны проходить:

```bash
uv run pytest
uv run kb-agent --query-fixture fixtures/queries/project_query.json --vault-root vault
uv run kb-eval --eval-fixture fixtures/evals/cases.json --vault-root vault
```

Live-путь нужен только если у вас есть `OPENAI_API_KEY` и вы хотите показать
финальный ответ через Responses API.

**Нужно ли делать optional «Живую Wiki»?**  
Нет. Для базовой сдачи достаточно локального проектного маршрута: тесты,
`kb-agent`, `kb-eval` и один читаемый `run_id`. «Живая Wiki» — это расширение
после базового среза, если вы уже всё сдали и хотите показать контролируемое
предложение изменений.

## Что сдавать в LMS

Минимальный пакет:

1. ссылка на репозиторий или архив;
2. commit SHA;
3. один проверенный `run_id`;
4. сводка `vault/outputs/<run_id>-summary.md`;
5. итоговый ответ `vault/outputs/<run_id>.md`;
6. `artifacts/source-map/<run_id>.json`;
7. `artifacts/health/<run_id>.json`;
8. eval-отчёт со статусом `pass`;
9. короткая заметка по `docs/handoff-template.md`, включая 2-3 строки про
   границы доверия.

Если преподаватель или ревьюер попросит детали, открывайте их по тому же
`run_id`: `artifacts/runs/`, `artifacts/plans/`, `artifacts/context/`,
`artifacts/tools/` и последние строки `artifacts/traces/<run_id>.jsonl`.

Весь репозиторий как простыню в LMS прикладывать не нужно.
