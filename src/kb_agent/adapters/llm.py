from __future__ import annotations


def _first_body_line(document: dict) -> str:
    for line in document["content"].splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return "Документ требует дополнительного разбора."


def compile_wiki_overview(documents: list[dict], concepts: list[dict] | None = None) -> str:
    lines = [
        "# index",
        "",
        "Этот файл собран автоматически из локального корпуса.",
        "",
    ]
    if concepts:
        lines.extend(["## Концепты", ""])
        for concept in concepts:
            lines.extend(
                [
                    f"### {concept['title']}",
                    f"- note: [[concepts/{concept['concept_id']}]]",
                    f"- gist: {concept['summary']}",
                    "",
                ]
            )
    lines.extend(
        [
        "## Документы",
        "",
        ]
    )
    for document in documents:
        lines.extend(
            [
                f"### {document['title']}",
                f"- source_id: `{document['source_id']}`",
                f"- note: [[sources/{document['source_id']}]]",
                f"- gist: {_first_body_line(document)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def compile_source_wiki_page(document: dict) -> str:
    lines = [
        f"# {document['title']}",
        "",
        "## Короткая выжимка",
        "",
        _first_body_line(document),
        "",
        "## Опорный источник",
        "",
        f"- [[raw/{document['source_id']}]]",
        "",
    ]
    return "\n".join(lines)


def compile_concept_wiki_page(concept: dict) -> str:
    lines = [
        f"# {concept['title']}",
        "",
        "## Короткая выжимка",
        "",
        concept["summary"],
        "",
        "## Связанные source pages",
        "",
    ]
    for source_id in concept["source_ids"]:
        lines.append(f"- [[sources/{source_id}]]")
    if concept.get("related_concepts"):
        lines.extend(["", "## Связанные концепты", ""])
        for concept_id in concept["related_concepts"]:
            lines.append(f"- [[concepts/{concept_id}]]")
    lines.extend(["", "## Опорные raw notes", ""])
    for source_id in concept["source_ids"]:
        lines.append(f"- [[raw/{source_id}]]")
    lines.append("")
    return "\n".join(lines)


def build_grounded_answer(
    query_fixture: dict,
    documents: list[dict],
    *,
    wiki_documents: list[dict] | None = None,
) -> str:
    lines = [
        f"# Ответ: {query_fixture['question']}",
        "",
        "## Короткий вывод",
        "",
    ]
    for document in documents:
        lines.append(f"- {_first_body_line(document)}")
    if wiki_documents:
        lines.extend(["", "## Через какие wiki-страницы был собран контекст", ""])
        for document in wiki_documents:
            lines.append(f"- [[wiki/{document['note_id']}]]")
    lines.extend(["", "## Цитаты", ""])
    for document in documents:
        lines.append(f"- [[raw/{document['source_id']}]]")
    lines.append("")
    return "\n".join(lines)
