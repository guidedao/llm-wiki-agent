from __future__ import annotations

import json
from pathlib import Path


REQUIRED_TRACE_EVENTS = [
    "query_loaded",
    "corpus_loaded",
    "wiki_compiled",
    "plan_created",
    "plan_context_selected",
    "context_packet_written",
    "answer_written",
    "plan_completed",
]


def _check(name: str, passed: bool, detail: str) -> dict:
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "detail": detail,
    }


def load_trace_events(trace_path: Path) -> list[dict]:
    if not trace_path.exists():
        return []
    events: list[dict] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def build_health_report(artifacts_dir: Path, run_id: str) -> dict:
    run_path = artifacts_dir / "runs" / f"{run_id}.json"
    trace_path = artifacts_dir / "traces" / f"{run_id}.jsonl"
    plan_path = artifacts_dir / "plans" / f"{run_id}.json"
    context_path = artifacts_dir / "context" / f"{run_id}.json"

    run_record = (
        json.loads(run_path.read_text(encoding="utf-8")) if run_path.exists() else {}
    )
    trace_events = load_trace_events(trace_path)
    event_names = [event.get("event") for event in trace_events]
    missing_events = [
        event_name for event_name in REQUIRED_TRACE_EVENTS if event_name not in event_names
    ]

    checks = [
        _check("run_record_exists", run_path.exists(), str(run_path)),
        _check(
            "run_completed",
            run_record.get("status") == "completed",
            f"status={run_record.get('status')!r}",
        ),
        _check(
            "terminal_reason_success",
            run_record.get("terminal_reason") == "success",
            f"terminal_reason={run_record.get('terminal_reason')!r}",
        ),
        _check("plan_artifact_exists", plan_path.exists(), str(plan_path)),
        _check("context_packet_exists", context_path.exists(), str(context_path)),
        _check("trace_exists", trace_path.exists(), str(trace_path)),
        _check(
            "trace_has_required_events",
            not missing_events,
            "missing=" + ", ".join(missing_events) if missing_events else "complete",
        ),
        _check(
            "answer_path_recorded",
            bool(run_record.get("answer_path")),
            str(run_record.get("answer_path")),
        ),
        _check(
            "wiki_path_recorded",
            bool(run_record.get("wiki_path")),
            str(run_record.get("wiki_path")),
        ),
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    return {
        "run_id": run_id,
        "status": status,
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "failed_count": sum(1 for check in checks if check["status"] == "fail"),
            "trace_event_count": len(trace_events),
        },
    }


def persist_health_report(artifacts_dir: Path, report: dict) -> Path:
    health_dir = artifacts_dir / "health"
    health_dir.mkdir(parents=True, exist_ok=True)
    path = health_dir / f"{report['run_id']}.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
