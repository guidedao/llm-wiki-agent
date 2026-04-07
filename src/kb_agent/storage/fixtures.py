from __future__ import annotations

import json
from pathlib import Path


def load_query_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_markdown_corpus(root: Path) -> list[dict]:
    documents: list[dict] = []
    for path in sorted(root.rglob("*.md")):
        content = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(root)
        note_id = relative_path.with_suffix("").as_posix()
        parts = relative_path.parts
        page_type = parts[0] if len(parts) > 1 else "root"
        title = path.stem.replace("-", " ").replace("_", " ").strip().title()
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped.removeprefix("# ").strip()
                break
        documents.append(
            {
                "source_id": path.stem,
                "path": str(path),
                "relative_path": relative_path.as_posix(),
                "note_id": note_id,
                "page_type": page_type,
                "title": title,
                "content": content,
            }
        )
    return documents
