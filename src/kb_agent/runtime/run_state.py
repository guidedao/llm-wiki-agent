from __future__ import annotations

import json
from pathlib import Path
from datetime import UTC, datetime
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def persist_run_record(
    artifacts_dir: Path,
    task_title: str,
    stage: str,
    run_id: str | None = None,
    answer_path: Path | None = None,
    wiki_path: Path | None = None,
    summary_path: Path | None = None,
    terminal_reason: str | None = None,
    answer_source: str | None = None,
    openai_response_metadata_path: Path | None = None,
) -> dict:
    run_id = run_id or str(uuid4())
    runs_dir = artifacts_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{run_id}.json"
    previous: dict = {}
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
    record = {
        "run_id": run_id,
        "task_title": task_title,
        "stage": stage,
        "status": "completed" if stage == "completed" else "running",
        "created_at": previous.get("created_at", utc_now_iso()),
        "updated_at": utc_now_iso(),
        "terminal_reason": terminal_reason,
        "answer_path": str(answer_path) if answer_path else None,
        "wiki_path": str(wiki_path) if wiki_path else None,
        "summary_path": str(summary_path) if summary_path else previous.get("summary_path"),
        "answer_source": answer_source or previous.get("answer_source"),
        "openai_response_metadata_path": (
            str(openai_response_metadata_path)
            if openai_response_metadata_path
            else previous.get("openai_response_metadata_path")
        ),
    }
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return record
