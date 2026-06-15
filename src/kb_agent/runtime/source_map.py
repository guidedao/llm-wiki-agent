from __future__ import annotations

import json
from pathlib import Path


def build_source_map(
    *,
    run_id: str,
    question: str,
    answer_path: Path,
    context_path: Path,
    wiki_documents: list[dict],
    raw_documents: list[dict],
    decision_ladder: list[dict],
) -> dict:
    """Собрать маленькую карту оснований ответа для одного запуска."""
    wiki_by_raw = _wiki_pages_by_raw_source(wiki_documents)
    return {
        "run_id": run_id,
        "question": question,
        "scope": "run_scoped",
        "purpose": (
            "context показывает, что модель увидела; source-map показывает, "
            "какие raw-источники поддерживают ответ"
        ),
        "answer_path": answer_path.as_posix(),
        "context_path": context_path.as_posix(),
        "evidence": [
            {
                "evidence_id": f"ev:{document['source_id']}",
                "claim": _first_body_paragraph(document),
                "raw_source": {
                    "source_id": document["source_id"],
                    "title": document["title"],
                    "path": f"vault/raw/{document['source_id']}.md",
                },
                "wiki_pages": wiki_by_raw.get(document["source_id"], []),
                "status": "supported",
            }
            for document in raw_documents
        ],
        "decision_ladder": decision_ladder,
    }


def persist_source_map(artifacts_dir: Path, source_map: dict) -> Path:
    source_map_dir = artifacts_dir / "source-map"
    source_map_dir.mkdir(parents=True, exist_ok=True)
    path = source_map_dir / f"{source_map['run_id']}.json"
    path.write_text(
        json.dumps(source_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _wiki_pages_by_raw_source(wiki_documents: list[dict]) -> dict[str, list[dict]]:
    by_source_id: dict[str, list[dict]] = {}
    for document in wiki_documents:
        for source_id in _raw_links(document.get("content", "")):
            by_source_id.setdefault(source_id, []).append(
                {
                    "note_id": document["note_id"],
                    "page_type": document["page_type"],
                    "title": document["title"],
                }
            )
    return by_source_id


def _raw_links(text: str) -> list[str]:
    links: list[str] = []
    cursor = 0
    while True:
        start = text.find("[[raw/", cursor)
        if start == -1:
            return links
        end = text.find("]]", start)
        if end == -1:
            return links
        source_id = text[start + len("[[raw/") : end]
        if source_id and source_id not in links:
            links.append(source_id)
        cursor = end + 2


def _first_body_paragraph(document: dict, *, max_chars: int = 220) -> str:
    paragraph_lines: list[str] = []
    started = False
    for line in document["content"].splitlines():
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        if stripped.startswith("#"):
            continue
        started = True
        paragraph_lines.append(stripped)
    if not paragraph_lines:
        return "Источник выбран как основание ответа, но требует ручного чтения."
    paragraph = " ".join(paragraph_lines)
    if len(paragraph) <= max_chars:
        return paragraph
    clipped = paragraph[: max_chars - 1].rsplit(" ", 1)[0]
    return clipped.rstrip(".,;:") + "..."
