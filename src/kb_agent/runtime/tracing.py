from __future__ import annotations

import json
from pathlib import Path


def append_trace(artifacts_dir: Path, run_id: str, event: dict) -> Path:
    traces_dir = artifacts_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    path = traces_dir / f"{run_id}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path
