from __future__ import annotations


def score_eval_case(case: dict, ranked_documents: list[dict]) -> dict:
    positive_ranked = [item for item in ranked_documents if item["score"] > 0]
    selected_sources = [item["document"]["source_id"] for item in positive_ranked]
    expected_sources = case.get("expected_sources", [])
    forbidden_sources = case.get("forbidden_sources", [])
    expected_behavior = case.get("expected_behavior", "answer")

    if expected_behavior == "abstain":
        passed = not positive_ranked
        failure_reason = None if passed else "ожидался отказ от ответа, но ретривал нашёл контекст"
    else:
        missing_sources = [
            source_id for source_id in expected_sources if source_id not in selected_sources
        ]
        leaked_sources = [
            source_id for source_id in forbidden_sources if source_id in selected_sources
        ]
        passed = not missing_sources and not leaked_sources
        failure_reason = None
        if missing_sources:
            failure_reason = "не найдены ожидаемые источники: " + ", ".join(missing_sources)
        if leaked_sources:
            leaked = "выбраны запрещённые источники: " + ", ".join(leaked_sources)
            failure_reason = f"{failure_reason}; {leaked}" if failure_reason else leaked

    return {
        "case_id": case["id"],
        "question": case["question"],
        "expected_behavior": expected_behavior,
        "selected_sources": selected_sources,
        "expected_sources": expected_sources,
        "forbidden_sources": forbidden_sources,
        "passed": passed,
        "failure_reason": failure_reason,
    }
