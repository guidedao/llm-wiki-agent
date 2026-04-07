from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4


def persist_run_record(
    artifacts_dir: Path,
    task_title: str,
    stage: str,
    run_id: str | None = None,
    answer_path: Path | None = None,
    wiki_path: Path | None = None,
) -> dict:
    run_id = run_id or str(uuid4())
    runs_dir = artifacts_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": run_id,
        "task_title": task_title,
        "stage": stage,
        "answer_path": str(answer_path) if answer_path else None,
        "wiki_path": str(wiki_path) if wiki_path else None,
    }
    (runs_dir / f"{run_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return record
