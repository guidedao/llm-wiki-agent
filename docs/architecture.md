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

Later milestones will add:

- wiki-aware tools;
- planning and bounded maintenance actions;
- runtime state, health checks, and retries;
- controlled write-back and evals.
