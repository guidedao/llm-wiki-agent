from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class OpenAIAnswer:
    output_text: str
    response_id: str | None
    model: str
    usage: dict | None


def build_grounded_answer_input(
    query_fixture: dict,
    documents: list[dict],
    *,
    wiki_documents: list[dict] | None = None,
) -> str:
    sections = [
        "Задача: ответить на вопрос по локальной базе знаний.",
        "",
        f"Вопрос: {query_fixture['question']}",
        "",
        "Используй только контекст ниже. Если контекста недостаточно, прямо скажи, чего не хватает.",
        "Ответ верни в Markdown с разделами: ## Короткий вывод, ## Основание, ## Источники.",
        "",
    ]
    if wiki_documents:
        sections.extend(["Wiki-страницы, через которые был собран контекст:", ""])
        for document in wiki_documents:
            sections.append(
                f"- note_id: {document['note_id']}; title: {document['title']}"
            )
        sections.append("")

    sections.extend(["Raw-источники:", ""])
    for document in documents:
        sections.extend(
            [
                f"--- source_id: {document['source_id']}",
                f"title: {document['title']}",
                document["content"].strip(),
                "",
            ]
        )
    return "\n".join(sections).strip()


def build_grounded_answer_with_openai(
    query_fixture: dict,
    documents: list[dict],
    *,
    wiki_documents: list[dict] | None = None,
    model: str = "gpt-5-mini",
    client: Any | None = None,
) -> OpenAIAnswer:
    if client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Для --live-openai нужна переменная OPENAI_API_KEY.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "Для --live-openai нужен пакет openai. Запустите команду через "
                "`uv run --extra openai ... --live-openai` или установите extra "
                "с OpenAI SDK."
            ) from exc
        client = OpenAI()

    response = client.responses.create(
        model=model,
        instructions=(
            "Ты аккуратный агент локальной базы знаний. Не выдумывай факты, "
            "не ссылайся на источники, которых нет в контексте, и явно отделяй "
            "вывод от основания."
        ),
        input=build_grounded_answer_input(
            query_fixture,
            documents,
            wiki_documents=wiki_documents,
        ),
    )
    return OpenAIAnswer(
        output_text=getattr(response, "output_text", "") or "",
        response_id=getattr(response, "id", None),
        model=getattr(response, "model", model) or model,
        usage=_dump_jsonable(getattr(response, "usage", None)),
    )


def persist_openai_response_metadata(
    artifacts_dir: Path,
    *,
    run_id: str,
    answer: OpenAIAnswer,
) -> Path:
    responses_dir = artifacts_dir / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    path = responses_dir / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "response_id": answer.response_id,
        "model": answer.model,
        "usage": answer.usage,
        "output_text_length": len(answer.output_text),
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _dump_jsonable(value: Any) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    return {"repr": repr(value)}
