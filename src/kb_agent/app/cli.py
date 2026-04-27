from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Any

from kb_agent.adapters.llm import (
    build_grounded_answer,
    compile_concept_wiki_page,
    compile_source_wiki_page,
    compile_wiki_overview,
)
from kb_agent.adapters.openai_responses import (
    build_grounded_answer_with_openai,
    persist_openai_response_metadata,
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
from kb_agent.storage.vault import (
    append_run_log,
    ensure_vault_scaffold,
    write_run_summary,
    write_vault_home,
)
from kb_agent.tools.contracts import default_tool_contracts, persist_tool_contracts


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"OPENAI_API_KEY\s*=", re.IGNORECASE),
    re.compile(r"(api[_-]?key|access[_-]?token|password)\s*[:=]", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def build_concept_catalog(corpus: list[dict]) -> list[dict]:
    by_source_id = {document["source_id"] for document in corpus}
    concepts = [
        {
            "concept_id": "northstar-operating-model",
            "title": "Операционная модель Northstar Compute",
            "summary": "Northstar Compute продаёт не абстрактные GPU, а управляемую capacity с понятными обещаниями, ограничениями и диагностикой.",
            "source_ids": ["company-brief", "capacity-planning-q2", "pricing-margin-memo"],
            "related_concepts": ["gpu-capacity-planning", "market-positioning"],
        },
        {
            "concept_id": "gpu-capacity-planning",
            "title": "Планирование GPU-capacity",
            "summary": "Capacity нужно читать как продуктовый контракт: выделенная capacity, burst-capacity и буфер влияют на обещания клиентам.",
            "source_ids": ["capacity-planning-q2", "customer-call-lumen-labs"],
            "related_concepts": ["customer-commitments", "northstar-operating-model"],
        },
        {
            "concept_id": "customer-commitments",
            "title": "Клиентские обещания",
            "summary": "Клиентам важны предсказуемый старт задач, прозрачные статусы, окна обслуживания и честные ограничения capacity.",
            "source_ids": ["customer-call-lumen-labs", "incident-aurora-17"],
            "related_concepts": ["gpu-capacity-planning", "incident-diagnostics"],
        },
        {
            "concept_id": "incident-diagnostics",
            "title": "Диагностика инцидентов",
            "summary": "Трейс, состояние запуска и клиентский статус должны сходиться, иначе очередь GPU выглядит как молчание системы.",
            "source_ids": ["incident-aurora-17"],
            "related_concepts": ["customer-commitments"],
        },
        {
            "concept_id": "market-positioning",
            "title": "Позиционирование на GPU-cloud рынке",
            "summary": "Northstar Compute конкурирует с hyperscalers, GPU-провайдерами, частными кластерами и colo-партнёрами.",
            "source_ids": ["market-competitors", "pricing-margin-memo"],
            "related_concepts": ["northstar-operating-model"],
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
        description="Запустить локальное демо агента базы знаний Guidedao.",
    )
    parser.add_argument(
        "--query-fixture",
        default="fixtures/queries/m0_query.json",
        help="Путь к JSON-файлу с фикстурой вопроса.",
    )
    parser.add_argument(
        "--question",
        default=None,
        help="Переопределить вопрос из фикстуры для локального разового запуска.",
    )
    parser.add_argument(
        "--vault-root",
        default="vault",
        help="Путь к корневой папке локального vault.",
    )
    parser.add_argument(
        "--live-openai",
        action="store_true",
        help="Использовать OpenAI Responses API для финального ответа.",
    )
    parser.add_argument(
        "--allow-live-private-context",
        action="store_true",
        help="Разрешить --live-openai, даже если локальный корпус похож на содержащий секреты.",
    )
    parser.add_argument(
        "--openai-model",
        default=None,
        help="Модель для --live-openai.",
    )
    return parser


def main(argv: list[str] | None = None, *, openai_client: Any | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    query_fixture = load_query_fixture(Path(args.query_fixture))
    if args.question:
        query_fixture = {**query_fixture, "question": args.question}
    vault_root = Path(args.vault_root)
    _reject_dangerous_output_root(vault_root, label="--vault-root")
    _reject_dangerous_output_root(settings.artifacts_dir, label="ARTIFACTS_DIR")
    ensure_vault_scaffold(vault_root)
    corpus = load_markdown_corpus(vault_root / "raw")
    if args.live_openai:
        _raise_if_live_context_looks_private(
            corpus,
            allow=args.allow_live_private_context,
        )
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
    tool_contracts = default_tool_contracts()
    tool_contracts_path = persist_tool_contracts(
        settings.artifacts_dir,
        run_id=run_record["run_id"],
        contracts=tool_contracts,
    )
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "tool_contracts_registered",
            "tool_contracts_path": str(tool_contracts_path),
            "tool_count": len(tool_contracts),
            "read_only_tools": [
                contract.name for contract in tool_contracts if contract.access == "read_only"
            ],
            "write_tools": [
                contract.name for contract in tool_contracts if contract.access == "write"
            ],
            "responses_ready_tools": [
                contract.name for contract in tool_contracts if contract.model_safe
            ],
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

    concept_ranked_all = rank_documents(query_fixture["question"], concept_pages, limit=3)
    concept_ranked = [item for item in concept_ranked_all if item["score"] > 0]
    concept_hits = [item["document"] for item in concept_ranked]
    source_ranked_all = rank_documents(query_fixture["question"], source_pages, limit=3)
    source_ranked_direct = [item for item in source_ranked_all if item["score"] > 0]
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "query_decision_entrypoint",
            "selected_entrypoint": "index",
            "reason": "стабильная входная страница wiki",
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
    source_resolution_entries = [*source_resolutions]
    resolved_source_note_ids = {item["document"]["note_id"] for item in source_resolution_entries}
    for item in source_ranked_direct:
        if item["document"]["note_id"] in resolved_source_note_ids:
            continue
        source_resolution_entries.append(
            {
                "document": item["document"],
                "linked_from": None,
                "reason": "термины вопроса напрямую совпали со страницей источника",
            }
        )
        resolved_source_note_ids.add(item["document"]["note_id"])
    source_hits = [item["document"] for item in source_resolution_entries]
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "source_page_resolution_finished",
            "matched_source_pages": [
                {
                    "note_id": item["document"]["note_id"],
                    "linked_from": item["linked_from"],
                    "reason": item.get("reason", "связано с выбранным концептом или индексной страницей"),
                }
                for item in source_resolution_entries
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
    raw_candidates = resolved_raw_documents or corpus
    raw_ranked_by_question = rank_documents(
        query_fixture["question"],
        raw_candidates,
        limit=3,
    )
    raw_ranked_by_plan = rank_documents(
        raw_query,
        raw_candidates,
        limit=3,
    )
    raw_ranked = _merge_ranked_documents(raw_ranked_by_question, raw_ranked_by_plan, limit=3)
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
                    "reason": "стабильная точка входа в wiki",
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
                    "reason": "термины вопроса совпали со страницей концепта",
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
                    "reason": "план создан до финального выбора raw-источников",
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
                    "reason": item.get("reason", "связано с выбранным концептом или индексной страницей"),
                }
                for item in source_resolution_entries
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
                    "reason": "финальный контекст ответа выбран из разрешённых raw-заметок",
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

    answer_source = "fixture"
    openai_metadata_path = None
    if args.live_openai:
        openai_answer = build_grounded_answer_with_openai(
            query_fixture,
            retrieved,
            wiki_documents=([wiki_index] if wiki_index else []) + concept_hits + source_hits,
            model=args.openai_model or settings.openai_model,
            client=openai_client,
        )
        answer = openai_answer.output_text
        answer_source = "openai_responses"
        openai_metadata_path = persist_openai_response_metadata(
            settings.artifacts_dir,
            run_id=run_record["run_id"],
            answer=openai_answer,
        )
        append_trace(
            artifacts_dir=settings.artifacts_dir,
            run_id=run_record["run_id"],
            event={
                "event": "openai_response_finished",
                "response_id": openai_answer.response_id,
                "model": openai_answer.model,
                "metadata_path": str(openai_metadata_path),
            },
        )
    else:
        answer = build_grounded_answer(
            query_fixture,
            retrieved,
            wiki_documents=([wiki_index] if wiki_index else []) + concept_hits + source_hits,
        )
    answers_dir = vault_root / "outputs"
    answers_dir.mkdir(parents=True, exist_ok=True)
    answer_path = answers_dir / f"{run_record['run_id']}.md"
    answer_path.write_text(answer, encoding="utf-8")
    health_path = settings.artifacts_dir / "health" / f"{run_record['run_id']}.json"
    trace_path = settings.artifacts_dir / "traces" / f"{run_record['run_id']}.jsonl"
    summary_path = write_run_summary(
        vault_root,
        run_id=run_record["run_id"],
        question=query_fixture["question"],
        answer_source=answer_source,
        wiki_path=wiki_path,
        answer_path=answer_path,
        matched_sources=[document["source_id"] for document in retrieved],
        artifact_paths={
            "plan": plan_path,
            "context": context_packet_path,
            "tools": tool_contracts_path,
            "trace": trace_path,
            "health": health_path,
            "openai_response": openai_metadata_path,
        },
    )
    write_vault_home(
        vault_root,
        wiki_path=wiki_path,
        answer_path=answer_path,
        summary_path=summary_path,
    )
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
            "answer_source": answer_source,
        },
    )
    append_trace(
        artifacts_dir=settings.artifacts_dir,
        run_id=run_record["run_id"],
        event={
            "event": "run_summary_written",
            "summary_path": str(summary_path),
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
        summary_path=summary_path,
        answer_source=answer_source,
        openai_response_metadata_path=openai_metadata_path,
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
    print(f"summary: {summary_path}")
    print(f"context: {context_packet_path}")
    print(f"tools: {tool_contracts_path}")
    print(f"trace: {settings.artifacts_dir / 'traces' / (run_record['run_id'] + '.jsonl')}")
    print(f"health: {health_path}")
    if openai_metadata_path:
        print(f"openai_response: {openai_metadata_path}")
    return 0


def _raise_if_live_context_looks_private(corpus: list[dict], *, allow: bool) -> None:
    if allow:
        return
    flagged = [
        document["source_id"]
        for document in corpus
        if any(pattern.search(document["content"]) for pattern in SECRET_PATTERNS)
    ]
    if flagged:
        raise RuntimeError(
            "--live-openai отправит выбранный локальный контекст в OpenAI, "
            "а локальный корпус похож на содержащий секреты. Проверьте эти "
            "источники или перезапустите команду с --allow-live-private-context: "
            + ", ".join(flagged)
        )


def _reject_dangerous_output_root(path: Path, *, label: str) -> None:
    resolved = path.expanduser().resolve()
    forbidden = {Path("/").resolve(), Path.home().resolve()}
    if resolved in forbidden:
        raise RuntimeError(f"{label} указывает на {resolved}; это слишком широкая область для демо-запуска.")


def _merge_ranked_documents(*ranked_lists: list[dict], limit: int) -> list[dict]:
    merged: list[dict] = []
    seen_source_ids: set[str] = set()
    for ranked in ranked_lists:
        for item in ranked:
            source_id = item["document"]["source_id"]
            if source_id in seen_source_ids:
                continue
            merged.append(item)
            seen_source_ids.add(source_id)
            if len(merged) >= limit:
                return merged
    return merged


if __name__ == "__main__":
    raise SystemExit(main())
