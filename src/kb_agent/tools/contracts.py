from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Literal


ToolAccess = Literal["read_only", "write"]


@dataclass(slots=True)
class ToolContract:
    name: str
    title: str
    description: str
    access: ToolAccess
    input_schema: dict
    output_schema: dict
    model_safe: bool
    requires_approval: bool = False
    writes_to: list[str] = field(default_factory=list)
    timeout_seconds: int = 5
    idempotent: bool = True

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "access": self.access,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "model_safe": self.model_safe,
            "requires_approval": self.requires_approval,
            "writes_to": self.writes_to,
            "timeout_seconds": self.timeout_seconds,
            "idempotent": self.idempotent,
        }

    def as_responses_tool(self) -> dict:
        if self.access != "read_only" or not self.model_safe:
            raise ValueError(f"{self.name} нельзя безопасно отдать модели как инструмент.")
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
            "strict": True,
        }


def default_tool_contracts() -> list[ToolContract]:
    return [
        ToolContract(
            name="compile_wiki_layer",
            title="Собрать wiki-слой",
            description="Собрать производные wiki-страницы из локального raw-корпуса.",
            access="write",
            input_schema=_object_schema(
                {
                    "raw_dir": {
                        "type": "string",
                        "description": "Папка с исходными Markdown-заметками.",
                    },
                    "wiki_dir": {
                        "type": "string",
                        "description": "Папка для сгенерированных wiki-страниц.",
                    },
                },
                required=["raw_dir", "wiki_dir"],
            ),
            output_schema=_object_schema(
                {
                    "wiki_index_path": {"type": "string"},
                    "source_page_count": {"type": "integer"},
                    "concept_page_count": {"type": "integer"},
                },
                required=["wiki_index_path", "source_page_count", "concept_page_count"],
            ),
            model_safe=False,
            writes_to=["vault/wiki/"],
            timeout_seconds=10,
            idempotent=True,
        ),
        ToolContract(
            name="search_wiki",
            title="Найти wiki-страницы",
            description="Найти релевантные wiki-страницы для вопроса пользователя.",
            access="read_only",
            input_schema=_object_schema(
                {
                    "query": {
                        "type": "string",
                        "description": "Вопрос пользователя или уточнённый запрос для ретривала.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Максимальное количество wiki-страниц в ответе.",
                    },
                },
                required=["query"],
            ),
            output_schema=_object_schema(
                {
                    "matches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "note_id": {"type": "string"},
                                "title": {"type": "string"},
                                "score": {"type": "number"},
                            },
                            "required": ["note_id", "title", "score"],
                            "additionalProperties": False,
                        },
                    }
                },
                required=["matches"],
            ),
            model_safe=True,
            writes_to=[],
            timeout_seconds=5,
            idempotent=True,
        ),
        ToolContract(
            name="read_raw_source",
            title="Прочитать raw-источник",
            description="Прочитать одну исходную заметку из raw-корпуса по source ID.",
            access="read_only",
            input_schema=_object_schema(
                {
                    "source_id": {
                        "type": "string",
                        "description": "ID исходной заметки без расширения файла.",
                    }
                },
                required=["source_id"],
            ),
            output_schema=_object_schema(
                {
                    "source_id": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
                required=["source_id", "title", "content"],
            ),
            model_safe=True,
            writes_to=[],
            timeout_seconds=5,
            idempotent=True,
        ),
        ToolContract(
            name="write_answer_artifact",
            title="Записать ответ запуска",
            description="Записать финальный Markdown-ответ запуска в vault/outputs.",
            access="write",
            input_schema=_object_schema(
                {
                    "run_id": {"type": "string"},
                    "markdown": {"type": "string"},
                },
                required=["run_id", "markdown"],
            ),
            output_schema=_object_schema(
                {
                    "answer_path": {"type": "string"},
                },
                required=["answer_path"],
            ),
            model_safe=False,
            writes_to=["vault/outputs/"],
            timeout_seconds=5,
            idempotent=False,
        ),
    ]


def responses_ready_tools(contracts: list[ToolContract]) -> list[dict]:
    return [contract.as_responses_tool() for contract in contracts if contract.model_safe]


def persist_tool_contracts(
    artifacts_dir: Path,
    *,
    run_id: str,
    contracts: list[ToolContract] | None = None,
) -> Path:
    contracts = contracts or default_tool_contracts()
    tools_dir = artifacts_dir / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    path = tools_dir / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "tools": [contract.as_dict() for contract in contracts],
        "responses_ready_tools": [
            contract.name for contract in contracts if contract.model_safe
        ],
        "active_live_openai_tools": [],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _object_schema(properties: dict, *, required: list[str]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }
