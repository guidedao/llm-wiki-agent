# Colab-ноутбуки к курсу

Этот каталог предназначен для коротких запускаемых примеров к урокам курса.
Ноутбуки хранятся в публичном GitHub-репозитории, а Colab открывает их по
ссылке вида:

```text
https://colab.research.google.com/github/guidedao/llm-wiki-agent/blob/main/notebooks/01_context_packet.ipynb
```

Такой способ лучше, чем хранить канонические ноутбуки в Google Drive:

* у курса есть один публичный канонический источник;
* студент не уходит в чужой Drive-файл с неочевидными правами доступа;
* каждый студент запускает свою копию в собственном Colab-сеансе;
* API-ключи не попадают в репозиторий и не шарятся через файл.

## Доступ и видимость

Репозиторий `guidedao/llm-wiki-agent` должен оставаться публичным, иначе Colab
ссылки не будут стабильно открываться у студентов без авторизации.

Google-аккаунт владельца для Drive здесь не критичен: каноническая копия живет
в GitHub. Если когда-нибудь понадобится именно Drive-владение под
`yo@guidedao.xyz`, это надо делать через авторизованную Google-сессию этого
аккаунта. Для учебного курса предпочтительный путь все равно GitHub -> Colab.

## Безопасность ключей

В ноутбуках нельзя хардкодить `OPENAI_API_KEY`.

Для примеров с реальным API используем один из двух вариантов:

* Colab Secrets;
* `getpass.getpass(...)` в ячейке, где студент вводит ключ вручную.

## Текущие Colab-ссылки

Ссылки заработают после публикации этих файлов в `main` публичного репозитория.

* [01_context_packet.ipynb](https://colab.research.google.com/github/guidedao/llm-wiki-agent/blob/main/notebooks/01_context_packet.ipynb)
* [02_context_surfaces.ipynb](https://colab.research.google.com/github/guidedao/llm-wiki-agent/blob/main/notebooks/02_context_surfaces.ipynb)
* [03_context_budget.ipynb](https://colab.research.google.com/github/guidedao/llm-wiki-agent/blob/main/notebooks/03_context_budget.ipynb)
* [04_context_builder.ipynb](https://colab.research.google.com/github/guidedao/llm-wiki-agent/blob/main/notebooks/04_context_builder.ipynb)
* [05_responses_api_context_call.ipynb](https://colab.research.google.com/github/guidedao/llm-wiki-agent/blob/main/notebooks/05_responses_api_context_call.ipynb)

## Редакторское правило

Ноутбук не заменяет урок. Он должен быть коротким практическим продолжением
одной идеи: контекстный пакет, поверхность контекста, бюджет, сборщик контекста
или минимальный вызов Responses API.

## Домены для ранних примеров

До кэпстоун-проекта ноутбуки не используют лор Northstar Compute. Ранние
примеры держатся ближе к типовым сценариям из документации OpenAI и Anthropic:
поддержка клиентов, возвраты, статусы заказов, поиск по FAQ, простые утилиты и
короткие документы.

Это сделано специально: сначала студент учится видеть механику API, контекста,
инструментов и схем без лишнего сюжетного веса. Полноценный лор Northstar
Compute появляется позже, в кэпстоун-проекте, где он уже нужен как рабочий
домен для живой LLM Wiki.
