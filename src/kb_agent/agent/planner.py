from __future__ import annotations

import json
from pathlib import Path

from kb_agent.agent.schemas import AnswerPlan, PlanStep
from kb_agent.retrieval.search import normalize_query_terms


def build_answer_plan(
    *,
    question: str,
    concept_documents: list[dict],
    source_documents: list[dict],
) -> AnswerPlan:
    focus_terms = _extract_focus_terms(question)
    concept_titles = [document["title"] for document in concept_documents]
    source_titles = [document["title"] for document in source_documents]

    steps: list[PlanStep] = []

    if concept_documents:
        steps.append(
            PlanStep(
                step_id="step-1",
                title="Снять рабочие концепты",
                goal="Понять, какие понятия из wiki задают рамку ответа до чтения raw notes.",
                retrieval_query=" ".join([question, *concept_titles[:2]]).strip(),
                target_layer="concepts",
                candidate_ids=[document["note_id"] for document in concept_documents],
            )
        )

    if source_documents:
        steps.append(
            PlanStep(
                step_id="step-2",
                title="Проверить опорные source pages",
                goal="Уточнить, какие source pages дают наиболее надёжную опору под вопрос.",
                retrieval_query=" ".join([question, *source_titles[:2]]).strip(),
                target_layer="sources",
                candidate_ids=[document["note_id"] for document in source_documents],
            )
        )

    steps.append(
        PlanStep(
            step_id=f"step-{len(steps) + 1}",
            title="Собрать grounded answer",
            goal="Поднять raw evidence и собрать ответ с явной привязкой к выбранному контексту.",
            retrieval_query=" ".join([question, *concept_titles[:2], *source_titles[:2]]).strip(),
            target_layer="raw",
            candidate_ids=[document["source_id"] for document in source_documents],
        )
    )

    return AnswerPlan(question=question, focus_terms=focus_terms, steps=steps)


def build_plan_step_context(
    plan: AnswerPlan,
    *,
    concept_documents: list[dict],
    source_documents: list[dict],
    raw_documents: list[dict],
) -> list[dict]:
    contexts: list[dict] = []
    for step in plan.steps:
        contexts.append(
            {
                "step_id": step.step_id,
                "target_layer": step.target_layer,
                "retrieval_query": step.retrieval_query,
                "selected_wiki_documents": [
                    _serialize_wiki_document(document)
                    for document in _documents_for_step(
                        step.target_layer,
                        concept_documents=concept_documents,
                        source_documents=source_documents,
                    )
                ],
                "selected_raw_documents": [
                    _serialize_raw_document(document)
                    for document in (raw_documents if step.target_layer == "raw" else [])
                ],
            }
        )
    return contexts


def persist_plan(artifacts_dir: Path, *, run_id: str, plan: AnswerPlan) -> Path:
    plans_dir = artifacts_dir / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    path = plans_dir / f"{run_id}.json"
    path.write_text(json.dumps(plan.as_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _extract_focus_terms(question: str) -> list[str]:
    stop_terms = {"что", "это", "про", "как", "для", "под", "или", "and", "the"}
    seen: list[str] = []
    for term in normalize_query_terms(question):
        if len(term) <= 2 or term in stop_terms or term in seen:
            continue
        seen.append(term)
    return seen


def _documents_for_step(
    target_layer: str,
    *,
    concept_documents: list[dict],
    source_documents: list[dict],
) -> list[dict]:
    if target_layer == "concepts":
        return concept_documents
    if target_layer == "sources":
        return source_documents
    return []


def _serialize_wiki_document(document: dict) -> dict:
    return {
        "note_id": document["note_id"],
        "page_type": document["page_type"],
        "title": document["title"],
    }


def _serialize_raw_document(document: dict) -> dict:
    return {
        "source_id": document["source_id"],
        "title": document["title"],
    }
