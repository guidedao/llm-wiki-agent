# llm-wiki-agent

Учебный capstone-репозиторий для курса «Разработка AI-агентов».

Это локальный агент базы знаний: он берёт небольшой markdown-корпус, собирает
из него wiki-слой, отвечает на вопрос с опорой на источники и оставляет
проверяемые артефакты запуска. Проект устроен как инженерная выпускная работа,
а не как абстрактная платформа для личных заметок.

Идея вдохновлена постом Андрея Карпати про «LLM Knowledge Bases» и
сопроводительным gist:

- пост в X:
  [Andrej Karpathy on X](https://x.com/karpathy/status/2040470801506541998)
- gist с идеей:
  [LLM Knowledge Bases gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

Мы используем эту идею как ориентир, а не как спецификацию и не как обещание
воспроизвести чужой workflow один в один. Внутри курса важнее другое:
локальный корпус, проверяемый wiki-слой, grounded answer, состояние запуска,
трейсы и понятный человеческий интерфейс через Obsidian.

## Форма проекта

Проект лучше всего понимать как несколько слоёв:

- локальный корпус исходных документов в `vault/raw/`;
- скомпилированный wiki-слой поверх этого корпуса;
- агент, который отвечает на вопросы по wiki и исходным файлам;
- runtime, который пишет состояние запуска, трейсы и markdown-выводы;
- Obsidian как удобный frontend для просмотра vault.

«Second Brain» здесь остаётся метафорой. Репозиторий не пытается стать
универсальной системой личных заметок.

## Зачем это в курсе

Этот capstone естественно связывает темы курса:

- вызовы LLM;
- локальную загрузку документов;
- retrieval;
- сборку контекста;
- markdown-выводы;
- состояние запуска и трейсы;
- будущие health checks и controlled write-back.

## Модель доставки

Проект должен оставаться самостоятельным для студента. Базовый путь должен
работать через:

- брифы в LMS;
- точные git-метки и коммиты;
- локальные команды `just demo` и `just test`;
- проверяемые артефакты в `vault/` и `artifacts/`;
- будущие solution-метки для сравнения.

Сгенерированные локальные артефакты запуска намеренно не входят в tracked
baseline репозитория. Студент создаёт их у себя через `just demo`.

## Политика зависимостей

Основной учебный путь должен запускаться без платных поисковых или социальных
API.

Обязательный минимум:

- Python `3.11`;
- `uv`;
- `just`;
- локальные fixtures и детерминированный тестовый режим.

Стандартный live LLM path курса:

- `OPENAI_API_KEY`.

Опциональные live-адаптеры:

- `Brave Search API` для живого веб-поиска.

Stretch-only адаптеры:

- `X API`.

Это означает:

- ни один базовый milestone не должен требовать `Brave Search API`;
- ни один базовый milestone не должен требовать `X API`;
- репозиторий всегда должен поддерживать fixture-backed path;
- ручной ввод URL остаётся допустимой альтернативой live search;
- текущий `M0` scaffold ещё не требует `OPENAI_API_KEY`.

См. также:

- [docs/dependency-policy.md](docs/dependency-policy.md)
- [docs/milestones/TEMPLATE.md](docs/milestones/TEMPLATE.md)
- [docs/milestones/m2.md](docs/milestones/m2.md)

## Текущий объём

Сейчас scaffold реализует узкий путь `M0 + ранний M2`:

- загружает небольшой локальный markdown-корпус;
- собирает overview wiki page, `sources/` и `concepts/` страницы в vault;
- отвечает на один фиксированный запрос через путь `index -> concepts -> sources -> raw notes`;
- создаёт проверяемый план ответа до финального ответа;
- связывает шаги плана с выбранным wiki- и raw-контекстом;
- пишет context packet, где видно, какие knowledge artifacts были выбраны;
- пишет markdown-ответ с цитированием источников;
- обновляет `vault/index.md` и `vault/log.md`;
- сохраняет простой run record и JSONL trace.

Уже на `M0` студент может открыть `vault/` в Obsidian и посмотреть:

- `vault/index.md`;
- `vault/log.md`;
- `vault/raw/`;
- `vault/wiki/index.md`;
- `vault/wiki/sources/<source_id>.md`;
- `vault/wiki/concepts/<concept_id>.md`;
- `vault/outputs/`.

Следующие milestone добавят:

- `M3`: состояние runtime, health checks и observability;
- `Stretch A`: controlled write-back;
- `Stretch B`: eval harness.

Важно:

- placeholder-модули уже лежат в `src/kb_agent/`;
- это поверхности будущих milestone, а не вся активная функциональность `M0`.

## Структура репозитория

```text
llm-wiki-agent/
  README.md
  pyproject.toml
  .env.example
  justfile
  vault/
    raw/
    wiki/
    outputs/
  src/kb_agent/
  tests/
  fixtures/
  docs/
  .github/workflows/ci.yml
```

## Команды

```bash
just setup
just demo
just test
```

Что делают команды:

- `just setup` устанавливает зависимости через `uv sync --frozen --extra dev`;
- `just demo` запускает demo path на fixture-запросе;
- `just test` запускает тесты проекта.

## Obsidian

Мы рекомендуем студентам установить бесплатное приложение Obsidian и открыть
локальную папку `vault/` как отдельный vault.

Obsidian удобен для просмотра knowledge artifacts, но основной путь остаётся
markdown-first и не зависит от конкретного редактора. Обычный редактор или
файловый браузер тоже подходят.

Гайд по настройке:

- [docs/obsidian-setup.md](docs/obsidian-setup.md)

## Что создаёт demo

Demo пишет student-visible knowledge artifacts в `vault/`:

- `vault/index.md`;
- `vault/log.md`;
- `vault/wiki/index.md`;
- `vault/wiki/sources/<source_id>.md`;
- `vault/wiki/concepts/<concept_id>.md`;
- `vault/outputs/<run_id>.md`.

Runtime artifacts пишутся в `artifacts/`:

- `context/<run_id>.json`;
- `runs/<run_id>.json`;
- `traces/<run_id>.jsonl`.

## Git-метки

Когда LMS ссылается на репозиторий, она должна вести на точные git-метки.
Метка — это фиксированная версия проекта для конкретного этапа курса.

Ожидаемые метки:

- `m0-start`;
- `m0-solution`;
- `m1-start`;
- `m1-solution`;
- `m2-start`;
- `m2-solution`;
- `m3-start`;
- `m3-solution`;
- `stretch-a-solution`;
- `stretch-b-solution`.
