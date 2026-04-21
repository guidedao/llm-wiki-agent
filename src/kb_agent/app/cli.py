from __future__ import annotations

import argparse
from pathlib import Path

from kb_agent.adapters.llm import (
    build_grounded_answer,
    compile_concept_wiki_page,
    compile_source_wiki_page,
    compile_wiki_overview,
)
from kb_agent.agent.planner import build_answer_plan, build_plan_step_context, persist_plan
from kb_agent.app.settings import load_settings
from kb_agent.health.checks import build_health_report, persist_health_report
from kb_agent.retrieval.context_packet import (
    persist_context_packet,
    resolve_raw_documents_with_reasons,
    resolve_wiki_documents_with_reasons,
)
from kb_agent.retrieval.search import rank_documents
from kb_agent.runtime.run_state import persist_run_record
from kb_agent.runtime.tracing import append_trace
from kb_agent.storage.fixtures import load_markdown_corpus, load_query_fixture
from kb_agent.storage.vault import append_run_log, ensure_vault_scaffold, write_vault_home


def build_concept_catalog(corpus: list[dict]) -> list[dict]:
    by_source_id = {document["source_id"] for document in corpus}
    concepts = [
        {
            "concept_id": "context-engineering",
            "title": "Контекст-инжиниринг",
            "summary": "Система должна собирать только нужные факты, ограничения и промежуточные результаты под конкретный запуск.",
            "source_ids": ["context-engineering"],
            "related_concepts": ["context-selection", "trace-grading"],
        },
        {
            "concept_id": "context-selection",
            "title": "Подбор контекста под задачу",
            "summary": "Хороший агент выбирает не максимум контекста, а именно те факты, которые нужны конкретному запуску.",
            "source_ids": ["context-engineering"],
            "related_concepts": ["context-engineering"],
        },
        {
            "concept_id": "trace-grading",
            "title": "Trace grading",
            "summary": "Качество агентной системы стоит оценивать не только по финальному ответу, но и по пути к нему.",
            "source_ids": ["runtime-traces"],
            "related_concepts": ["runtime-diagnosis", "context-engineering"],
        },
        {
            "concept_id": "runtime-diagnosis",
            "title": "Диагностика через trace",
            "summary": "Trace помогает разбирать плохой выбор инструмента, неудачный handoff и ошибки в оценке состояния запуска.",
            "source_ids": ["runtime-traces"],
            "related_concepts": ["trace-grading"],
        },
    ]
    return [
        concept
        for concept in concepts
        if all(source_id in by_source_id for source_id in concept["source_ids"])
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kb-agent",
        description="Run the Guidedao local knowledge-base agent demo.",
    )
    parser.add_argument(
        "--query-fixture",
        default="fixtures/queries/m0_query.json",
        help="Path to a query fixture JSON file.",
    )
    parser.add_argument(
        "--vault-root",
        default="vault",
        help="Path to the local Obsidian-friendly vault root.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = load_settings()
    query_fixture = load_query_fixture(Path(args.query_fixture))
    vault_root = Path(args.vault_root)
    ensure_vault_scaffold(vault_root)
    corpus = load_markdown_corpus(vault_root / "raw")
    concepts = build_concept_catalog(corpus)

    run_record = persist_run_record(
        artifacts_dir=settings.artifacts_dir,
        task_title=query_fixture["question"],
        stage="started",
    )

    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "query_loaded",
            "question": query_fixture["question"],
        },
    )
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "corpus_loaded",
            "document_count": len(corpus),
        },
    )

    wiki_dir = vault_root / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    wiki_path = wiki_dir / "index.md"
    sources_dir = wiki_dir / "sources"
    concepts_dir = wiki_dir / "concepts"
    sources_dir.mkdir(parents=True, exist_ok=True)
    concepts_dir.mkdir(parents=True, exist_ok=True)
    wiki_path.write_text(compile_wiki_overview(corpus, concepts), encoding="utf-8")
    for document in corpus:
        legacy_root_page = wiki_dir / f"{document['source_id']}.md"
        if legacy_root_page.exists():
            legacy_root_page.unlink()
        (sources_dir / f"{document['source_id']}.md").write_text(
            compile_source_wiki_page(document),
            encoding="utf-8",
        )
    for concept in concepts:
        (concepts_dir / f"{concept['concept_id']}.md").write_text(
            compile_concept_wiki_page(concept),
            encoding="utf-8",
        )

    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "wiki_compiled",
            "wiki_path": str(wiki_path),
        },
    )

    wiki_documents = load_markdown_corpus(wiki_dir)
    wiki_index = next(
        (document for document in wiki_documents if document["note_id"] == "index"),
        None,
    )
    concept_pages = [document for document in wiki_documents if document["page_type"] == "concepts"]
    source_pages = [document for document in wiki_documents if document["page_type"] == "sources"]

    concept_ranked = rank_documents(query_fixture["question"], concept_pages, limit=3)
    concept_hits = [item["document"] for item in concept_ranked]
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "query_decision_entrypoint",
            "selected_entrypoint": "index",
            "reason": "stable wiki landing page",
        },
    )
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "wiki_retrieval_finished",
            "matched_wiki_pages": [
                {
                    "note_id": item["document"]["note_id"],
                    "score": item["score"],
                    "matched_terms": item["matched_terms"],
                }
                for item in concept_ranked
            ],
        },
    )

    source_resolution_seed = concept_hits or ([wiki_index] if wiki_index else [])
    source_resolutions = resolve_wiki_documents_with_reasons(
        source_resolution_seed,
        source_pages,
        prefix="sources/",
    )
    source_hits = [item["document"] for item in source_resolutions]
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "source_page_resolution_finished",
            "matched_source_pages": [
                {
                    "note_id": item["document"]["note_id"],
                    "linked_from": item["linked_from"],
                }
                for item in source_resolutions
            ],
        },
    )

    plan = build_answer_plan(
        question=query_fixture["question"],
        concept_documents=concept_hits,
        source_documents=source_hits,
    )
    plan_path = persist_plan(
        settings.artifacts_dir,
        run_id=run_record["run_id"],
        plan=plan,
    )
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "plan_created",
            "plan_path": str(plan_path),
            "step_ids": [step.step_id for step in plan.steps],
        },
    )

    raw_resolution_seed = source_hits or source_resolution_seed
    raw_resolutions = resolve_raw_documents_with_reasons(raw_resolution_seed, corpus)
    resolved_raw_documents = [item["document"] for item in raw_resolutions]
    raw_query = plan.steps[-1].retrieval_query if plan.steps else query_fixture["question"]
    raw_ranked = rank_documents(
        raw_query,
        resolved_raw_documents or corpus,
        limit=2,
    )
    retrieved = [item["document"] for item in raw_ranked]
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "retrieval_finished",
            "matched_sources": [
                {
                    "source_id": item["document"]["source_id"],
                    "score": item["score"],
                    "matched_terms": item["matched_terms"],
                }
                for item in raw_ranked
            ],
        },
    )

    plan_step_context = build_plan_step_context(
        plan,
        concept_documents=concept_hits,
        source_documents=source_hits,
        raw_documents=retrieved,
    )
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "plan_context_selected",
            "step_context_counts": [
                {
                    "step_id": item["step_id"],
                    "wiki_count": len(item["selected_wiki_documents"]),
                    "raw_count": len(item["selected_raw_documents"]),
                }
                for item in plan_step_context
            ],
        },
    )

    decision_ladder = [
        {
            "stage": "entrypoint",
            "selected": [
                {
                    "note_id": "index",
                    "reason": "stable wiki entrypoint",
                }
            ],
        },
        {
            "stage": "concept_selection",
            "selected": [
                {
                    "note_id": item["document"]["note_id"],
                    "score": item["score"],
                    "matched_terms": item["matched_terms"],
                    "reason": "query terms matched concept page",
                }
                for item in concept_ranked
            ],
        },
        {
            "stage": "answer_plan",
            "selected": [
                {
                    "step_id": step.step_id,
                    "target_layer": step.target_layer,
                    "candidate_ids": step.candidate_ids,
                    "reason": "plan created before final raw selection",
                }
                for step in plan.steps
            ],
        },
        {
            "stage": "source_resolution",
            "selected": [
                {
                    "note_id": item["document"]["note_id"],
                    "linked_from": item["linked_from"],
                    "reason": "linked from selected concept or index page",
                }
                for item in source_resolutions
            ],
        },
        {
            "stage": "raw_selection",
            "selected": [
                {
                    "source_id": item["document"]["source_id"],
                    "score": item["score"],
                    "matched_terms": item["matched_terms"],
                    "linked_from": next(
                        (
                            resolution["linked_from"]
                            for resolution in raw_resolutions
                            if resolution["document"]["source_id"] == item["document"]["source_id"]
                        ),
                        None,
                    ),
                    "reason": "final answer context selected from resolved raw notes",
                }
                for item in raw_ranked
            ],
        },
    ]

    context_packet_path = persist_context_packet(
        settings.artifacts_dir,
        run_id=run_record["run_id"],
        question=query_fixture["question"],
        plan=plan.as_dict(),
        plan_step_context=plan_step_context,
        wiki_documents=([wiki_index] if wiki_index else []) + concept_hits + source_hits,
        raw_documents=retrieved,
        decision_ladder=decision_ladder,
    )
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "context_packet_written",
            "context_packet_path": str(context_packet_path),
        },
    )

    answer = build_grounded_answer(
        query_fixture,
        retrieved,
        wiki_documents=([wiki_index] if wiki_index else []) + concept_hits + source_hits,
    )
    answers_dir = vault_root / "outputs"
    answers_dir.mkdir(parents=True, exist_ok=True)
    answer_path = answers_dir / f"{run_record['run_id']}.md"
    answer_path.write_text(answer, encoding="utf-8")
    write_vault_home(vault_root, wiki_path=wiki_path, answer_path=answer_path)
    log_path = append_run_log(
        vault_root,
        run_id=run_record["run_id"],
        question=query_fixture["question"],
        wiki_path=wiki_path,
        answer_path=answer_path,
        matched_sources=[document["source_id"] for document in retrieved],
    )

    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "answer_written",
            "answer_path": str(answer_path),
        },
    )
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "plan_completed",
            "plan_path": str(plan_path),
            "answer_path": str(answer_path),
        },
    )
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "vault_log_updated",
            "log_path": str(log_path),
        },
    )

    persist_run_record(
        artifacts_dir=settings.artifacts_dir,
        task_title=query_fixture["question"],
        run_id=run_record["run_id"],
        stage="completed",
        terminal_reason="success",
        answer_path=answer_path,
        wiki_path=wiki_path,
    )
    health_report = build_health_report(settings.artifacts_dir, run_record["run_id"])
    health_path = persist_health_report(settings.artifacts_dir, health_report)
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "health_report_written",
            "health_path": str(health_path),
            "health_status": health_report["status"],
        },
    )

    print(f"run_id: {run_record['run_id']}")
    print(f"query: {query_fixture['question']}")
    print(f"vault: {vault_root / 'index.md'}")
    print(f"wiki: {wiki_path}")
    print(f"log: {log_path}")
    print(f"answer: {answer_path}")
    print(f"context: {context_packet_path}")
    print(f"trace: {settings.artifacts_dir / 'traces' / (run_record['run_id'] + '.jsonl')}")
    print(f"health: {health_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
