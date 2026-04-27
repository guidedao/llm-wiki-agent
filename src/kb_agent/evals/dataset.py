from __future__ import annotations

import json
from pathlib import Path


def load_eval_cases(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload["cases"] if isinstance(payload, dict) else payload
    if not isinstance(cases, list):
        raise ValueError("Eval-фикстура должна содержать список кейсов.")
    return cases
