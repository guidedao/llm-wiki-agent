from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from kb_agent.adapters.openai_responses import (
    build_grounded_answer_input,
    build_grounded_answer_with_openai,
    persist_openai_response_metadata,
)


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="resp_123",
            model=kwargs["model"],
            output_text="# Ответ\n\nТестовый live-ответ.",
            usage={"input_tokens": 10, "output_tokens": 5},
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_openai_responses_adapter_uses_fake_client():
    client = FakeClient()
    query = {"question": "Что база говорит про инцидент Aurora-17?"}
    documents = [
        {
            "source_id": "incident-aurora-17",
            "title": "Инцидент Aurora-17",
            "content": "Трейс показывает путь запуска и причину задержки.",
        }
    ]
    wiki_documents = [
        {
            "note_id": "concepts/incident-diagnostics",
            "title": "Диагностика инцидентов",
        }
    ]

    answer = build_grounded_answer_with_openai(
        query,
        documents,
        wiki_documents=wiki_documents,
        model="gpt-test",
        client=client,
    )

    call = client.responses.calls[0]
    assert call["model"] == "gpt-test"
    assert "Что база говорит про инцидент Aurora-17?" in call["input"]
    assert "incident-aurora-17" in call["input"]
    assert "concepts/incident-diagnostics" in call["input"]
    assert answer.response_id == "resp_123"
    assert answer.model == "gpt-test"
    assert answer.output_text.startswith("# Ответ")
    assert answer.usage == {"input_tokens": 10, "output_tokens": 5}


def test_openai_responses_requires_api_key_when_client_is_not_injected(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_grounded_answer_with_openai({"question": "test"}, [], model="gpt-test")


def test_openai_response_metadata_persists_without_raw_answer(tmp_path):
    client = FakeClient()
    answer = build_grounded_answer_with_openai(
        {"question": "test"},
        [{"source_id": "s1", "title": "S1", "content": "content"}],
        model="gpt-test",
        client=client,
    )

    path = persist_openai_response_metadata(tmp_path, run_id="run-1", answer=answer)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["run_id"] == "run-1"
    assert payload["response_id"] == "resp_123"
    assert payload["model"] == "gpt-test"
    assert payload["usage"] == {"input_tokens": 10, "output_tokens": 5}
    assert "Тестовый live-ответ" not in path.read_text(encoding="utf-8")


def test_grounded_answer_input_keeps_task_small_and_source_bound():
    text = build_grounded_answer_input(
        {"question": "Что такое буфер capacity?"},
        [
            {
                "source_id": "capacity-planning-q2",
                "title": "Capacity planning Q2",
                "content": "Буфер нужен, чтобы reserved-клиенты не ждали старт задач.",
            }
        ],
    )

    assert "Используй только контекст ниже" in text
    assert "capacity-planning-q2" in text
    assert "## Короткий вывод" in text
