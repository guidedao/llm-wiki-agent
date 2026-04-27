from __future__ import annotations

import argparse
from pathlib import Path

from kb_agent.app.settings import load_settings
from kb_agent.app.cli import _reject_dangerous_output_root
from kb_agent.evals.dataset import load_eval_cases
from kb_agent.evals.harness import persist_eval_report, run_eval_suite
from kb_agent.storage.fixtures import load_markdown_corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kb-eval",
        description="Запустить маленький детерминированный eval-набор wiki-агента.",
    )
    parser.add_argument(
        "--eval-fixture",
        default="fixtures/evals/cases.json",
        help="Путь к JSON-файлу с eval-кейсами.",
    )
    parser.add_argument(
        "--vault-root",
        default="vault",
        help="Путь к корневой папке локального vault.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    _reject_dangerous_output_root(Path(args.vault_root), label="--vault-root")
    _reject_dangerous_output_root(settings.artifacts_dir, label="ARTIFACTS_DIR")
    cases = load_eval_cases(Path(args.eval_fixture))
    corpus = load_markdown_corpus(Path(args.vault_root) / "raw")
    report = run_eval_suite(cases, corpus)
    report_path = persist_eval_report(settings.artifacts_dir, report)

    print(f"eval_run_id: {report['eval_run_id']}")
    print(f"status: {report['status']}")
    print(f"passed: {report['summary']['passed_count']}/{report['summary']['case_count']}")
    print(f"report: {report_path}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
