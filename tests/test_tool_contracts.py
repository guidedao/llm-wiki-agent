from __future__ import annotations

import json

import pytest

from kb_agent.tools.contracts import (
    default_tool_contracts,
    persist_tool_contracts,
    responses_ready_tools,
)


def test_tool_contracts_separate_read_and_write_surfaces():
    contracts = default_tool_contracts()
    by_name = {contract.name: contract for contract in contracts}

    assert by_name["search_wiki"].access == "read_only"
    assert by_name["read_raw_source"].access == "read_only"
    assert by_name["compile_wiki_layer"].access == "write"
    assert by_name["write_answer_artifact"].writes_to == ["vault/outputs/"]
    assert not by_name["write_answer_artifact"].model_safe


def test_responses_ready_tools_export_only_read_only_contracts():
    tools = responses_ready_tools(default_tool_contracts())
    names = {tool["name"] for tool in tools}

    assert names == {"search_wiki", "read_raw_source"}
    assert all(tool["type"] == "function" for tool in tools)
    assert all(tool["strict"] is True for tool in tools)
    assert all(tool["parameters"]["additionalProperties"] is False for tool in tools)


def test_write_contract_is_not_exportable_as_model_tool():
    write_contract = next(
        contract for contract in default_tool_contracts() if contract.name == "write_answer_artifact"
    )

    with pytest.raises(ValueError, match="нельзя безопасно"):
        write_contract.as_responses_tool()


def test_tool_contracts_persist_as_run_artifact(tmp_path):
    path = persist_tool_contracts(tmp_path, run_id="run-1")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["run_id"] == "run-1"
    assert "search_wiki" in payload["responses_ready_tools"]
    assert payload["active_live_openai_tools"] == []
    assert any(tool["access"] == "write" for tool in payload["tools"])
