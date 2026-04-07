from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


def ensure_vault_scaffold(vault_root: Path) -> None:
    (vault_root / "raw").mkdir(parents=True, exist_ok=True)
    (vault_root / "wiki").mkdir(parents=True, exist_ok=True)
    (vault_root / "outputs").mkdir(parents=True, exist_ok=True)

    index_path = vault_root / "index.md"
    if not index_path.exists():
        index_path.write_text(_render_vault_home(), encoding="utf-8")

    log_path = vault_root / "log.md"
    if not log_path.exists():
        log_path.write_text(_render_log_header(), encoding="utf-8")


def write_vault_home(
    vault_root: Path,
    wiki_path: Path | None = None,
    answer_path: Path | None = None,
) -> Path:
    index_path = vault_root / "index.md"
    index_path.write_text(
        _render_vault_home(vault_root=vault_root, wiki_path=wiki_path, answer_path=answer_path),
        encoding="utf-8",
    )
    return index_path


def append_run_log(
    vault_root: Path,
    *,
    run_id: str,
    question: str,
    wiki_path: Path,
    answer_path: Path,
    matched_sources: list[str],
) -> Path:
    log_path = vault_root / "log.md"
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    source_links = ", ".join(f"[[raw/{source_id}]]" for source_id in matched_sources) or "none"
    entry = "\n".join(
        [
            f"## {timestamp} · {run_id}",
            "",
            f"- Вопрос: {question}",
            f"- Wiki: {_to_wikilink(vault_root, wiki_path)}",
            f"- Ответ: {_to_wikilink(vault_root, answer_path)}",
            f"- Источники: {source_links}",
            "",
        ]
    )
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)
    return log_path


def _render_vault_home(
    vault_root: Path | None = None,
    wiki_path: Path | None = None,
    answer_path: Path | None = None,
) -> str:
    lines = [
        "# Vault Index",
        "",
        "Этот vault обслуживает local-first knowledge agent.",
        "",
        "## Навигация",
        "",
        "- [[wiki/index]]",
        "- [[log]]",
        "- [[raw/context-engineering]]",
        "- [[raw/runtime-traces]]",
    ]
    if vault_root and wiki_path:
        lines.extend(["", "## Последний запуск", "", f"- Wiki: {_to_wikilink(vault_root, wiki_path)}"])
        if answer_path:
            lines.append(f"- Ответ: {_to_wikilink(vault_root, answer_path)}")
    lines.append("")
    return "\n".join(lines)


def _render_log_header() -> str:
    return "\n".join(
        [
            "# Run Log",
            "",
            "Здесь фиксируются запуски demo и их главные артефакты.",
            "",
        ]
    )


def _to_wikilink(vault_root: Path, path: Path) -> str:
    relative = path.relative_to(vault_root)
    stemmed = relative.with_suffix("")
    return f"[[{stemmed.as_posix()}]]"
