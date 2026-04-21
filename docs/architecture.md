# Architecture Notes

The capstone is intentionally CLI-first and local-first.

Human-facing browsing happens through Obsidian over the repo `vault/`.

Current `M0` path:

1. keep `vault/index.md` and `vault/log.md` as first-class navigation artifacts;
2. load a local markdown corpus from `vault/raw/`;
3. compile one overview wiki page into `vault/wiki/index.md`;
4. retrieve relevant local documents for a fixed query;
5. write a grounded markdown answer into `vault/outputs/`;
6. persist a run record and trace into `artifacts/`.

Current `M1` slice:

1. compile `vault/wiki/sources/` and `vault/wiki/concepts/`;
2. query the wiki layer first through `index -> concepts -> sources`;
3. resolve source notes from wiki links;
4. persist a context packet into `artifacts/context/`.

Current `M2` slice:

1. build a short answer plan before the final answer;
2. persist `artifacts/plans/<run_id>.json`;
3. link plan steps to selected wiki and raw context;
4. write planning events into the JSONL trace.

Current `M3` slice:

1. treat `artifacts/runs/<run_id>.json` as the run state record;
2. mark successful completion with a terminal reason;
3. write `artifacts/health/<run_id>.json` as a machine-readable health report;
4. keep `run_budget.yaml` as the readable budget by runtime stage.

Later milestones will add:

- wiki-aware tools;
- richer planning and bounded maintenance actions;
- retries, pause/resume, and operator remediation;
- controlled write-back and evals.
