from __future__ import annotations


STOP_TERMS = {
    "and",
    "compute",
    "northstar",
    "the",
    "wiki",
    "база",
    "базе",
    "базу",
    "говорит",
    "знаний",
    "какая",
    "какие",
    "какой",
    "как",
    "компания",
    "описана",
    "описано",
    "описаны",
    "под",
    "про",
    "что",
    "это",
}


def normalize_query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for item in query.split():
        term = item.strip(".,:;!?()[]{}\"'").lower()
        if not term or len(term) <= 2 or term in STOP_TERMS:
            continue
        terms.append(term)
    return terms


def rank_documents(query: str, documents: list[dict], limit: int = 2) -> list[dict]:
    query_terms = normalize_query_terms(query)
    scored: list[dict] = []
    for document in documents:
        haystack = f"{document['title']} {document['content']}".lower()
        matched_terms = [term for term in query_terms if term and term in haystack]
        scored.append(
            {
                "document": document,
                "score": len(matched_terms),
                "matched_terms": matched_terms,
            }
        )
    scored.sort(key=lambda item: (item["score"], item["document"]["source_id"]), reverse=True)
    positive = [item for item in scored if item["score"] > 0]
    if positive:
        return positive[:limit]
    return scored[:limit]


def search_documents(query: str, documents: list[dict], limit: int = 2) -> list[dict]:
    return [item["document"] for item in rank_documents(query, documents, limit=limit)]
