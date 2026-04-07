# guidedao-local-kb-agent

Capstone repository scaffold for the course `Разработка AI-агентов`.

This project is a local knowledge-base agent inspired by the `Second Brain`
idea, but scoped as a concrete engineering capstone instead of a vague personal
knowledge platform.

The framing is inspired by Andrej Karpathy's April 2026 `LLM Knowledge Bases`
X post and companion gist:

- X post:
  [Andrej Karpathy on X](https://x.com/karpathy/status/2040470801506541998)
- idea gist:
  [LLM Knowledge Bases gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

In practice, the idea is:

- a local `raw/` corpus;
- an automatically compiled `wiki/` layer that later gains a live LLM path;
- question answering over the knowledge base, with later bounded maintenance;
- a human-readable frontend like Obsidian.

We use this as an inspiration pattern, not as a spec or a promise to recreate
Karpathy's exact workflow.

## Product Shape

The project is best understood as:

- a local corpus of source documents;
- a compiled wiki layer built from that corpus;
- an agent that answers grounded questions against the wiki and source files;
- a runtime that writes traces, run state, and markdown outputs;
- Obsidian as the human-facing frontend for browsing the vault.

We keep `Second Brain` as a metaphor, not as the exact repo or package name.

## Why This Capstone

It naturally connects:

- LLM calls;
- local ingestion;
- retrieval;
- context assembly;
- markdown outputs;
- run state and traces;
- later health checks and controlled write-back.

## Delivery Model

This capstone should remain self-sustaining for the student.

That means the core path should work through:

- LMS milestone briefings
- exact repo tags and commits
- local commands like `just demo` and `just test`
- inspectable artifacts in `vault/` and `artifacts/`
- later solution tags for comparison

It should not depend on mentor intervention as part of the default path.

Local generated run artifacts are intentionally not part of the tracked repo
baseline. Students should produce them locally through `just demo`.

## Dependency Policy

The core student path must stay runnable without extra paid search or social
API subscriptions.

Core required path:

- Python `3.11`
- `uv`
- `just`
- local fixtures and deterministic test mode

Course-default live LLM path:

- `OPENAI_API_KEY`

Optional live adapters:

- `Brave Search API` for live web search

Stretch-only adapters:

- `X API`

This means:

- no core milestone should require `Brave Search API`;
- no core milestone should require `X API`;
- the repository must always support a fixture-backed path;
- manual URL input should remain a valid alternative to live search.
- current `M0` scaffold does not require `OPENAI_API_KEY` yet.

See:

- `docs/dependency-policy.md`
- `docs/milestones/TEMPLATE.md`
- `docs/milestones/m2.md`

## Current Scope

The current scaffold implements a narrow `M0 + early M2` path:

- load a small local markdown corpus;
- compile one overview wiki page plus `sources/` and `concepts/` wiki pages into the vault;
- answer one fixed query through the `index -> concepts -> sources -> raw notes` path;
- create an inspectable answer plan before the final answer;
- link plan steps to selected wiki and raw context;
- write a context packet that shows which knowledge artifacts were selected;
- write a markdown answer with citations;
- keep `vault/index.md` and `vault/log.md` up to date;
- persist a simple run record and JSONL trace.

For `M0`, students can already open `vault/` in Obsidian and inspect:

- `vault/index.md`
- `vault/log.md`
- `vault/raw/`
- `vault/wiki/index.md`
- `vault/wiki/sources/<source_id>.md`
- `vault/wiki/concepts/<concept_id>.md`
- `vault/outputs/`

Later milestones will add:

- `M3`: runtime state, health checks, and observability;
- `Stretch A`: controlled write-back;
- `Stretch B`: eval harness.

Important:

- placeholder modules already exist in `src/kb_agent/`;
- they are future milestone surfaces, not active functionality in `M0`.

## Repo Shape

```text
guidedao-local-kb-agent/
  README.md
  pyproject.toml
  .env.example
  justfile
  vault/
    raw/
    wiki/
    outputs/
  src/kb_agent/
  tests/
  fixtures/
  docs/
  .github/workflows/ci.yml
```

## Commands

- `just setup`
- `just demo`
- `just test`

## Obsidian

We recommend that students install the free Obsidian app and open the repo's
local `vault/` folder as a vault.

Obsidian is the most convenient way to browse the knowledge artifacts in this
capstone, but the core path remains markdown-first and editor-agnostic. Any
editor or file browser still works.

Setup guide:

- [docs/obsidian-setup.md](docs/obsidian-setup.md)

## Demo Output

The demo writes student-visible knowledge artifacts into `vault/`:

- `vault/index.md`
- `vault/log.md`
- `vault/wiki/index.md`
- `vault/wiki/sources/<source_id>.md`
- `vault/wiki/concepts/<concept_id>.md`
- `vault/outputs/<run_id>.md`

It also writes runtime artifacts to `artifacts/`:

- `context/<run_id>.json`
- `runs/<run_id>.json`
- `traces/<run_id>.jsonl`

## Tag Policy

When this becomes a public repo, LMS should link to exact tags:

- `m0-start`
- `m0-solution`
- `m1-start`
- `m1-solution`
- `m2-start`
- `m2-solution`
- `m3-start`
- `m3-solution`
- `stretch-a-solution`
- `stretch-b-solution`
