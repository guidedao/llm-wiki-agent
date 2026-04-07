from __future__ import annotations

import json
from pathlib import Path


def extract_wikilinks(text: str) -> list[str]:
    links: list[str] = []
    cursor = 0
    while True:
        start = text.find("[[", cursor)
        if start == -1:
            return links
        end = text.find("]]", start)
        if end == -1:
            return links
        links.append(text[start + 2 : end])
        cursor = end + 2


def resolve_raw_documents_from_wiki(
    wiki_documents: list[dict],
    raw_documents: list[dict],
) -> list[dict]:
    return [
        item["document"]
        for item in resolve_raw_documents_with_reasons(wiki_documents, raw_documents)
    ]


def resolve_wiki_documents_from_wiki(
    wiki_documents: list[dict],
    universe: list[dict],
    *,
    prefix: str,
) -> list[dict]:
    return [
        item["document"]
        for item in resolve_wiki_documents_with_reasons(
            wiki_documents,
            universe,
            prefix=prefix,
        )
    ]


def resolve_raw_documents_with_reasons(
    wiki_documents: list[dict],
    raw_documents: list[dict],
) -> list[dict]:
    raw_by_id = {document["source_id"]: document for document in raw_documents}
    resolved: list[dict] = []
    seen: set[str] = set()
    for wiki_document in wiki_documents:
        for link in extract_wikilinks(wiki_document["content"]):
            if not link.startswith("raw/"):
                continue
            source_id = link.removeprefix("raw/")
            if source_id in raw_by_id and source_id not in seen:
                resolved.append(
                    {
                        "document": raw_by_id[source_id],
                        "linked_from": wiki_document["note_id"],
                    }
                )
                seen.add(source_id)
    return resolved


def resolve_wiki_documents_with_reasons(
    wiki_documents: list[dict],
    universe: list[dict],
    *,
    prefix: str,
) -> list[dict]:
    universe_by_note_id = {document["note_id"]: document for document in universe}
    resolved: list[dict] = []
    seen: set[str] = set()
    for wiki_document in wiki_documents:
        for link in extract_wikilinks(wiki_document["content"]):
            if not link.startswith(prefix):
                continue
            if link in universe_by_note_id and link not in seen:
                resolved.append(
                    {
                        "document": universe_by_note_id[link],
                        "linked_from": wiki_document["note_id"],
                    }
                )
                seen.add(link)
    return resolved


def persist_context_packet(
    artifacts_dir: Path,
    *,
    run_id: str,
    question: str,
    wiki_documents: list[dict],
    raw_documents: list[dict],
    decision_ladder: list[dict],
) -> Path:
    context_dir = artifacts_dir / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    packet = {
        "run_id": run_id,
        "question": question,
        "wiki_documents": [
            {
                "source_id": document["source_id"],
                "note_id": document["note_id"],
                "page_type": document["page_type"],
                "title": document["title"],
            }
            for document in wiki_documents
        ],
        "raw_documents": [
            {
                "source_id": document["source_id"],
                "title": document["title"],
            }
            for document in raw_documents
        ],
        "decision_ladder": decision_ladder,
    }
    path = context_dir / f"{run_id}.json"
    path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
