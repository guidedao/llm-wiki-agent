# Майлстоуны кэпстоун-проекта

Эта папка нужна для совместимости с LMS-уроками, где кэпстоун разбит на
контрольные точки `M2` и `M3`.

В актуальной версии репозитория базовая сдача проще: студент проходит один
проектный маршрут из `docs/final-project.md`, а эти файлы помогают понять, как
старые LMS-контрольные точки ложатся на тот же запуск.

Основной маршрут:

```bash
uv sync --frozen --extra dev
uv run pytest
uv run kb-agent --query-fixture fixtures/queries/project_query.json --vault-root vault
uv run kb-eval --eval-fixture fixtures/evals/cases.json --vault-root vault
```

После запуска читайте один `run_id`: summary, answer, source-map, context,
trace, health и eval.

