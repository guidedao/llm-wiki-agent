from __future__ import annotations

import json
from pathlib import Path
import shutil
from types import SimpleNamespace

from kb_agent.adapters.llm import (
    build_grounded_answer,
    compile_concept_wiki_page,
    compile_source_wiki_page,
    compile_wiki_overview,
)
from kb_agent.agent.planner import build_answer_plan, build_plan_step_context, persist_plan
from kb_agent.app.cli import build_concept_catalog, main as cli_main
from kb_agent.health.checks import build_health_report, persist_health_report
from kb_agent.retrieval.context_packet import (
    persist_context_packet,
    resolve_raw_documents_with_reasons,
    resolve_wiki_documents_with_reasons,
)
from kb_agent.runtime.run_state import persist_run_record
from kb_agent.runtime.tracing import append_trace
from kb_agent.retrieval.search import rank_documents, search_documents
from kb_agent.storage.fixtures import load_markdown_corpus, load_query_fixture
from kb_agent.storage.vault import (
    append_run_log,
    ensure_vault_scaffold,
    write_run_summary,
    write_vault_home,
)
from kb_agent.tools.contracts import persist_tool_contracts


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="resp_e2e",
            model=kwargs["model"],
            output_text="## Короткий вывод\n\nLive-путь прошёл через тестовый клиент.",
            usage={"input_tokens": 30, "output_tokens": 12},
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_m0_query_builds_grounded_answer():
    root = Path(__file__).resolve().parents[1]
    query = load_query_fixture(root / "fixtures" / "queries" / "m0_query.json")
    corpus = load_markdown_corpus(root / "vault" / "raw")
    retrieved = search_documents(query["question"], corpus)
    answer = build_grounded_answer(query, retrieved)
    assert "## Цитаты" in answer
    assert "[[raw/capacity-planning-q2]]" in answer
    assert "[[raw/customer-call-lumen-labs]]" in answer or "[[raw/incident-aurora-17]]" in answer


def test_corpus_loads_and_compiles_overview():
    root = Path(__file__).resolve().parents[1]
    corpus = load_markdown_corpus(root / "vault" / "raw")
    concepts = build_concept_catalog(corpus)
    overview = compile_wiki_overview(corpus, concepts)
    assert len(corpus) == 6
    assert "# Индекс" in overview
    assert "[[concepts/gpu-capacity-planning]]" in overview
    assert "Northstar Compute" in overview


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
    concepts = build_concept_catalog(corpus)
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
        "Зачем Lumen Labs нужен буфер capacity?",
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
    plan = build_answer_plan(
        question="Зачем Lumen Labs нужен буфер capacity?",
        concept_documents=[item["document"] for item in concept_ranked],
        source_documents=source_hits,
    )
    plan_path = persist_plan(tmp_path / "artifacts", run_id="run-1", plan=plan)
    plan_step_context = build_plan_step_context(
        plan,
        concept_documents=[item["document"] for item in concept_ranked],
        source_documents=source_hits,
        raw_documents=resolved_raw,
    )
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
        question="Зачем Lumen Labs нужен буфер capacity?",
        plan=plan.as_dict(),
        plan_step_context=plan_step_context,
        wiki_documents=concept_hits + source_hits,
        raw_documents=resolved_raw,
        decision_ladder=decision_ladder,
    )

    context_text = context_path.read_text(encoding="utf-8")
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    assert any(document["note_id"] == "index" for document in concept_hits)
    assert any(document["note_id"] == "concepts/gpu-capacity-planning" for document in concept_hits)
    assert any(document["note_id"] == "sources/capacity-planning-q2" for document in source_hits)
    assert "capacity-planning-q2" in context_text
    assert "decision_ladder" in context_text
    assert "plan_step_context" in context_text
    assert "matched_terms" in context_text
    assert len(plan_payload["steps"]) >= 3
    assert plan_payload["steps"][-1]["target_layer"] == "raw"


def test_vault_home_and_log_are_written(tmp_path):
    vault_root = tmp_path / "vault"
    ensure_vault_scaffold(vault_root)

    wiki_path = vault_root / "wiki" / "index.md"
    wiki_path.write_text("# Индекс\n", encoding="utf-8")
    answer_path = vault_root / "outputs" / "run-1.md"
    answer_path.write_text("# Ответ\n", encoding="utf-8")
    summary_path = vault_root / "outputs" / "run-1-summary.md"
    summary_path.write_text("# Сводка\n", encoding="utf-8")

    write_vault_home(
        vault_root,
        wiki_path=wiki_path,
        answer_path=answer_path,
        summary_path=summary_path,
    )
    append_run_log(
        vault_root,
        run_id="run-1",
        question="Что говорит база знаний про планирование capacity?",
        wiki_path=wiki_path,
        answer_path=answer_path,
        matched_sources=["capacity-planning-q2", "customer-call-lumen-labs"],
    )

    index_text = (vault_root / "index.md").read_text(encoding="utf-8")
    log_text = (vault_root / "log.md").read_text(encoding="utf-8")

    assert "[[wiki/index]]" in index_text
    assert "[[outputs/run-1]]" in index_text
    assert "[[outputs/run-1-summary]]" in index_text
    assert "Что говорит база знаний" in log_text
    assert "[[raw/capacity-planning-q2]]" in log_text


def test_run_summary_points_to_answer_and_runtime_artifacts(tmp_path):
    vault_root = tmp_path / "vault"
    ensure_vault_scaffold(vault_root)
    wiki_path = vault_root / "wiki" / "index.md"
    answer_path = vault_root / "outputs" / "run-1.md"
    wiki_path.write_text("# Индекс\n", encoding="utf-8")
    answer_path.write_text("# Ответ\n", encoding="utf-8")

    summary_path = write_run_summary(
        vault_root,
        run_id="run-1",
        question="Что говорит база знаний?",
        answer_source="fixture",
        wiki_path=wiki_path,
        answer_path=answer_path,
        matched_sources=["company-brief"],
        artifact_paths={
            "plan": tmp_path / "artifacts" / "plans" / "run-1.json",
            "context": tmp_path / "artifacts" / "context" / "run-1.json",
            "tools": tmp_path / "artifacts" / "tools" / "run-1.json",
            "trace": tmp_path / "artifacts" / "traces" / "run-1.jsonl",
            "health": tmp_path / "artifacts" / "health" / "run-1.json",
            "openai_response": None,
        },
    )

    text = summary_path.read_text(encoding="utf-8")
    assert "[[outputs/run-1]]" in text
    assert "[[raw/company-brief]]" in text
    assert "`tools`:" in text
    assert "Модель не получает права менять" in text


def test_health_report_checks_core_run_artifacts(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    run_id = "run-1"
    persist_run_record(
        artifacts_dir,
        task_title="Проверить запуск",
        stage="started",
        run_id=run_id,
    )
    for event_name in [
        "query_loaded",
        "corpus_loaded",
        "tool_contracts_registered",
        "wiki_compiled",
        "plan_created",
        "plan_context_selected",
        "context_packet_written",
        "answer_written",
        "run_summary_written",
        "plan_completed",
    ]:
        append_trace(artifacts_dir, run_id, {"event": event_name})
    (artifacts_dir / "plans").mkdir(parents=True)
    (artifacts_dir / "plans" / f"{run_id}.json").write_text(
        json.dumps({"steps": []}) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "context").mkdir(parents=True)
    (artifacts_dir / "context" / f"{run_id}.json").write_text(
        json.dumps({"decision_ladder": []}) + "\n",
        encoding="utf-8",
    )
    persist_tool_contracts(artifacts_dir, run_id=run_id)
    summary_path = tmp_path / "vault" / "outputs" / "run-1-summary.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("# Сводка\n", encoding="utf-8")
    persist_run_record(
        artifacts_dir,
        task_title="Проверить запуск",
        stage="completed",
        run_id=run_id,
        terminal_reason="success",
        answer_path=tmp_path / "vault" / "outputs" / "run-1.md",
        wiki_path=tmp_path / "vault" / "wiki" / "index.md",
        summary_path=summary_path,
    )

    report = build_health_report(artifacts_dir, run_id)
    report_path = persist_health_report(artifacts_dir, report)

    assert report["status"] == "pass"
    assert report["summary"]["failed_count"] == 0
    assert report_path.exists()


def test_cli_live_openai_path_is_e2e_testable_without_api_key(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    vault_root = tmp_path / "vault"
    artifacts_dir = tmp_path / "artifacts"
    shutil.copytree(root / "vault" / "raw", vault_root / "raw")
    monkeypatch.setenv("ARTIFACTS_DIR", str(artifacts_dir))
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = FakeClient()
    exit_code = cli_main(
        [
            "--query-fixture",
            str(root / "fixtures" / "queries" / "m0_query.json"),
            "--vault-root",
            str(vault_root),
            "--live-openai",
        ],
        openai_client=client,
    )

    assert exit_code == 0
    call = client.responses.calls[0]
    assert call["model"] == "gpt-test"
    assert "Wiki-страницы" in call["input"]
    assert "Raw-источники" in call["input"]

    response_paths = list((artifacts_dir / "responses").glob("*.json"))
    assert len(response_paths) == 1
    response_payload = json.loads(response_paths[0].read_text(encoding="utf-8"))
    run_id = response_payload["run_id"]
    run_record = json.loads(
        (artifacts_dir / "runs" / f"{run_id}.json").read_text(encoding="utf-8")
    )
    health_report = json.loads(
        (artifacts_dir / "health" / f"{run_id}.json").read_text(encoding="utf-8")
    )
    answer_text = (vault_root / "outputs" / f"{run_id}.md").read_text(encoding="utf-8")
    summary_text = (
        vault_root / "outputs" / f"{run_id}-summary.md"
    ).read_text(encoding="utf-8")

    assert run_record["answer_source"] == "openai_responses"
    assert run_record["openai_response_metadata_path"] == str(response_paths[0])
    assert run_record["summary_path"].endswith(f"{run_id}-summary.md")
    assert health_report["status"] == "pass"
    assert any(
        check["name"] == "openai_response_metadata_exists"
        and check["status"] == "pass"
        for check in health_report["checks"]
    )
    assert "Live-путь прошёл" in answer_text
    assert "openai_responses" in summary_text
    assert "openai_response" in summary_text


def test_cli_custom_question_can_retrieve_new_raw_source(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    vault_root = tmp_path / "vault"
    artifacts_dir = tmp_path / "artifacts"
    shutil.copytree(root / "vault" / "raw", vault_root / "raw")
    (vault_root / "raw" / "approval-gates.md").write_text(
        "\n".join(
            [
                "# Гейты подтверждения",
                "",
                "Гейты подтверждения останавливают рискованные действия агента до записи.",
                "Агент готовит предложение, человек видит предпросмотр, а приложение применяет изменение после подтверждения.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ARTIFACTS_DIR", str(artifacts_dir))

    exit_code = cli_main(
        [
            "--vault-root",
            str(vault_root),
            "--question",
            "Что база говорит про гейты подтверждения?",
        ],
    )

    assert exit_code == 0
    assert (vault_root / "wiki" / "sources" / "approval-gates.md").exists()
    run_paths = list((artifacts_dir / "runs").glob("*.json"))
    run_id = json.loads(run_paths[0].read_text(encoding="utf-8"))["run_id"]
    answer_text = (vault_root / "outputs" / f"{run_id}.md").read_text(encoding="utf-8")
    context_text = (artifacts_dir / "context" / f"{run_id}.json").read_text(
        encoding="utf-8"
    )

    assert "[[raw/approval-gates]]" in answer_text
    assert "approval-gates" in context_text


def test_live_openai_blocks_obvious_secrets_in_local_context(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    vault_root = tmp_path / "vault"
    artifacts_dir = tmp_path / "artifacts"
    shutil.copytree(root / "vault" / "raw", vault_root / "raw")
    (vault_root / "raw" / "secret-note.md").write_text(
        "# Секретная заметка\n\nOPENAI_API_KEY=sk-test-secret-value-that-should-not-ship\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARTIFACTS_DIR", str(artifacts_dir))

    try:
        cli_main(
            [
                "--vault-root",
                str(vault_root),
                "--live-openai",
            ],
            openai_client=FakeClient(),
        )
    except RuntimeError as exc:
        assert "secret-note" in str(exc)
    else:
        raise AssertionError("live-путь OpenAI должен блокировать очевидные локальные секреты")
