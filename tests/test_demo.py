from __future__ import annotations

from pathlib import Path

from kb_agent.adapters.llm import (
    build_grounded_answer,
    compile_concept_wiki_page,
    compile_source_wiki_page,
    compile_wiki_overview,
)
from kb_agent.retrieval.context_packet import (
    persist_context_packet,
    resolve_raw_documents_with_reasons,
    resolve_wiki_documents_with_reasons,
)
from kb_agent.retrieval.search import rank_documents, search_documents
from kb_agent.storage.fixtures import load_markdown_corpus, load_query_fixture
from kb_agent.storage.vault import append_run_log, ensure_vault_scaffold, write_vault_home


def test_m0_query_builds_grounded_answer():
    root = Path(__file__).resolve().parents[1]
    query = load_query_fixture(root / "fixtures" / "queries" / "m0_query.json")
    corpus = load_markdown_corpus(root / "vault" / "raw")
    retrieved = search_documents(query["question"], corpus)
    answer = build_grounded_answer(query, retrieved)
    assert "## Цитаты" in answer
    assert "[[raw/context-engineering]]" in answer or "[[raw/runtime-traces]]" in answer


def test_corpus_loads_and_compiles_overview():
    root = Path(__file__).resolve().parents[1]
    corpus = load_markdown_corpus(root / "vault" / "raw")
    concepts = [
        {
            "concept_id": "context-engineering",
            "title": "Контекст-инжиниринг",
            "summary": "Контекст собирается под конкретный запуск.",
            "source_ids": ["context-engineering"],
            "related_concepts": ["context-selection"],
        }
    ]
    overview = compile_wiki_overview(corpus, concepts)
    assert len(corpus) == 2
    assert "# index" in overview
    assert "[[concepts/context-engineering]]" in overview
    assert "Контекст-инжиниринг" in overview


def test_query_fixture_loader_reads_json():
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "queries" / "m0_query.json"
    )
    query = load_query_fixture(fixture_path)
    assert "question" in query


def test_wiki_pages_drive_context_selection(tmp_path):
    root = Path(__file__).resolve().parents[1]
    corpus = load_markdown_corpus(root / "vault" / "raw")

    wiki_dir = tmp_path / "wiki"
    sources_dir = wiki_dir / "sources"
    concepts_dir = wiki_dir / "concepts"
    sources_dir.mkdir(parents=True, exist_ok=True)
    concepts_dir.mkdir(parents=True, exist_ok=True)
    for document in corpus:
        (sources_dir / f"{document['source_id']}.md").write_text(
            compile_source_wiki_page(document),
            encoding="utf-8",
        )
    concepts = [
        {
            "concept_id": "context-engineering",
            "title": "Контекст-инжиниринг",
            "summary": "Контекст собирается под конкретный запуск.",
            "source_ids": ["context-engineering"],
            "related_concepts": ["context-selection"],
        },
        {
            "concept_id": "context-selection",
            "title": "Подбор контекста под задачу",
            "summary": "Нужно выбирать только нужные факты.",
            "source_ids": ["context-engineering"],
            "related_concepts": ["context-engineering"],
        },
        {
            "concept_id": "trace-grading",
            "title": "Trace grading",
            "summary": "Нужно смотреть не только на итог, но и на путь.",
            "source_ids": ["runtime-traces"],
            "related_concepts": ["runtime-diagnosis"],
        },
        {
            "concept_id": "runtime-diagnosis",
            "title": "Диагностика через trace",
            "summary": "Trace помогает разбирать ошибки выбора.",
            "source_ids": ["runtime-traces"],
            "related_concepts": ["trace-grading"],
        },
    ]
    for concept in concepts:
        (concepts_dir / f"{concept['concept_id']}.md").write_text(
            compile_concept_wiki_page(concept),
            encoding="utf-8",
        )
    (wiki_dir / "index.md").write_text(compile_wiki_overview(corpus, concepts), encoding="utf-8")

    wiki_documents = load_markdown_corpus(wiki_dir)
    wiki_index = next(document for document in wiki_documents if document["note_id"] == "index")
    concept_pages = [document for document in wiki_documents if document["page_type"] == "concepts"]
    source_pages = [document for document in wiki_documents if document["page_type"] == "sources"]
    concept_ranked = rank_documents(
        "Что база знаний говорит про контекст-инжиниринг и trace grading?",
        concept_pages,
        limit=3,
    )
    concept_hits = [wiki_index, *[item["document"] for item in concept_ranked]]
    source_resolutions = resolve_wiki_documents_with_reasons(
        concept_hits,
        source_pages,
        prefix="sources/",
    )
    source_hits = [item["document"] for item in source_resolutions]
    raw_resolutions = resolve_raw_documents_with_reasons(source_hits, corpus)
    resolved_raw = [item["document"] for item in raw_resolutions]
    decision_ladder = [
        {
            "stage": "concept_selection",
            "selected": [
                {
                    "note_id": item["document"]["note_id"],
                    "score": item["score"],
                    "matched_terms": item["matched_terms"],
                }
                for item in concept_ranked
            ],
        }
    ]
    context_path = persist_context_packet(
        tmp_path / "artifacts",
        run_id="run-1",
        question="Что база знаний говорит про контекст-инжиниринг и trace grading?",
        wiki_documents=concept_hits + source_hits,
        raw_documents=resolved_raw,
        decision_ladder=decision_ladder,
    )

    context_text = context_path.read_text(encoding="utf-8")
    assert any(document["note_id"] == "index" for document in concept_hits)
    assert any(document["note_id"] == "concepts/context-engineering" for document in concept_hits)
    assert any(document["note_id"] == "sources/context-engineering" for document in source_hits)
    assert "context-engineering" in context_text
    assert "decision_ladder" in context_text
    assert "matched_terms" in context_text


def test_vault_home_and_log_are_written(tmp_path):
    vault_root = tmp_path / "vault"
    ensure_vault_scaffold(vault_root)

    wiki_path = vault_root / "wiki" / "index.md"
    wiki_path.write_text("# index\n", encoding="utf-8")
    answer_path = vault_root / "outputs" / "run-1.md"
    answer_path.write_text("# answer\n", encoding="utf-8")

    write_vault_home(vault_root, wiki_path=wiki_path, answer_path=answer_path)
    append_run_log(
        vault_root,
        run_id="run-1",
        question="Что говорит база знаний про контекст-инжиниринг?",
        wiki_path=wiki_path,
        answer_path=answer_path,
        matched_sources=["context-engineering", "runtime-traces"],
    )

    index_text = (vault_root / "index.md").read_text(encoding="utf-8")
    log_text = (vault_root / "log.md").read_text(encoding="utf-8")

    assert "[[wiki/index]]" in index_text
    assert "[[outputs/run-1]]" in index_text
    assert "Что говорит база знаний" in log_text
    assert "[[raw/context-engineering]]" in log_text
