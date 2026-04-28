from __future__ import annotations

import json
from pathlib import Path

from kb_agent.evals.dataset import load_eval_cases
from kb_agent.evals.harness import persist_eval_report, run_eval_suite
from kb_agent.storage.fixtures import load_markdown_corpus


def test_eval_suite_covers_grounding_and_abstain_cases(tmp_path):
    root = Path(__file__).resolve().parents[1]
    cases = load_eval_cases(root / "fixtures" / "evals" / "cases.json")
    corpus = load_markdown_corpus(root / "vault" / "raw")

    report = run_eval_suite(cases, corpus)
    report_path = persist_eval_report(tmp_path, report)
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert payload["status"] == "pass"
    assert payload["summary"]["case_count"] == 5
    assert any(
        result["expected_behavior"] == "abstain" and result["passed"]
        for result in payload["results"]
    )
