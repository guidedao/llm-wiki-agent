from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PlanStep:
    step_id: str
    title: str
    goal: str
    retrieval_query: str
    target_layer: str
    candidate_ids: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "goal": self.goal,
            "retrieval_query": self.retrieval_query,
            "target_layer": self.target_layer,
            "candidate_ids": self.candidate_ids,
        }


@dataclass(slots=True)
class AnswerPlan:
    question: str
    focus_terms: list[str] = field(default_factory=list)
    steps: list[PlanStep] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "question": self.question,
            "focus_terms": self.focus_terms,
            "steps": [step.as_dict() for step in self.steps],
        }
