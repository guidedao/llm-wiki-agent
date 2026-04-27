from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from kb_agent.evals.score import score_eval_case
from kb_agent.retrieval.search import rank_documents


def run_eval_suite(cases: list[dict], corpus: list[dict]) -> dict:
    results: list[dict] = []
    for case in cases:
        ranked = rank_documents(case["question"], corpus, limit=case.get("limit", 2))
        results.append(score_eval_case(case, ranked))

    passed_count = sum(1 for result in results if result["passed"])
    status = "pass" if passed_count == len(results) else "fail"
    return {
        "eval_run_id": str(uuid4()),
        "status": status,
        "summary": {
            "case_count": len(results),
            "passed_count": passed_count,
            "failed_count": len(results) - passed_count,
        },
        "results": results,
    }


def persist_eval_report(artifacts_dir: Path, report: dict) -> Path:
    evals_dir = artifacts_dir / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    path = evals_dir / f"{report['eval_run_id']}.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
