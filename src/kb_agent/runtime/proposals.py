from __future__ import annotations

from dataclasses import dataclass
from difflib import unified_diff
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WikiUpdateProposal:
    run_id: str
    question: str
    status: str
    target_path: str
    source_ids: list[str]
    rationale: str
    proposed_section: str

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "question": self.question,
            "status": self.status,
            "target_path": self.target_path,
            "source_ids": self.source_ids,
            "rationale": self.rationale,
            "proposed_section": self.proposed_section,
        }


def build_wiki_update_proposal(
    *,
    run_id: str,
    question: str,
    target_path: Path,
    raw_documents: list[dict],
) -> WikiUpdateProposal:
    source_ids = [document["source_id"] for document in raw_documents]
    evidence = ", ".join(source_ids) if source_ids else "нет выбранных raw-источников"
    proposed_section = "\n".join(
        [
            f"## Candidate update from run {run_id}",
            "",
            f"- Вопрос: {question}",
            f"- Основание: {evidence}",
            "- Статус: proposal only; не применять без preview и явного подтверждения.",
            "",
        ]
    )
    return WikiUpdateProposal(
        run_id=run_id,
        question=question,
        status="proposal_only_not_applied",
        target_path=target_path.as_posix(),
        source_ids=source_ids,
        rationale=(
            "Запуск нашёл материалы, которые могут усилить устойчивый wiki-слой. "
            "Proposal показывает возможное изменение, но не пишет в vault/wiki."
        ),
        proposed_section=proposed_section,
    )


def persist_wiki_update_proposal(
    artifacts_dir: Path,
    *,
    proposal: WikiUpdateProposal,
) -> dict[str, Path]:
    proposals_dir = artifacts_dir / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)

    target_path = Path(proposal.target_path)
    current_text = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
    current_lines = current_text.splitlines(keepends=True)
    proposed_text = _append_section(current_text, proposal.proposed_section)
    proposed_lines = proposed_text.splitlines(keepends=True)
    diff_text = "".join(
        unified_diff(
            current_lines,
            proposed_lines,
            fromfile=proposal.target_path,
            tofile=f"{proposal.target_path} (proposal)",
        )
    )

    json_path = proposals_dir / f"{proposal.run_id}.json"
    diff_path = proposals_dir / f"{proposal.run_id}.diff"
    markdown_path = proposals_dir / f"{proposal.run_id}.md"

    json_path.write_text(
        json.dumps(
            {
                **proposal.as_dict(),
                "proposal_json_path": json_path.as_posix(),
                "proposal_diff_path": diff_path.as_posix(),
                "proposal_markdown_path": markdown_path.as_posix(),
                "applied": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    diff_path.write_text(diff_text, encoding="utf-8")
    markdown_path.write_text(_render_markdown(proposal, diff_text), encoding="utf-8")

    return {
        "proposal": json_path,
        "diff": diff_path,
        "markdown": markdown_path,
    }


def _append_section(current_text: str, section: str) -> str:
    if not current_text.strip():
        return section
    return current_text.rstrip() + "\n\n" + section


def _render_markdown(proposal: WikiUpdateProposal, diff_text: str) -> str:
    sources = ", ".join(proposal.source_ids) if proposal.source_ids else "нет"
    return "\n".join(
        [
            f"# Proposal: {proposal.run_id}",
            "",
            f"- Статус: `{proposal.status}`",
            f"- Целевая страница: `{proposal.target_path}`",
            f"- Источники: {sources}",
            "",
            "## Почему",
            "",
            proposal.rationale,
            "",
            "## Preview",
            "",
            "```diff",
            diff_text.rstrip(),
            "```",
            "",
            "## Guardrail",
            "",
            "Это только proposal. Модель не применяет patch и не пишет в `vault/wiki/`.",
            "",
        ]
    )
